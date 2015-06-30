#!/usr/bin/env python

import numpy as np

from scipy.special import legendre
from scipy.optimize import fsolve

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm


def compute_gauss_points_and_weights(order):

    coefs = legendre(order)

    p = np.poly1d(coefs)  

    coefs_prime = (np.arange(len(coefs) + 1)[::-1] * coefs)[:-1]

    p_prime = np.poly1d(coefs_prime)  

    points = fsolve(p, np.linspace(-1, 1, num=order))

    weights = 2.0 / ((1 - points * points) * p_prime(points) * p_prime(points))

    return points, weights


class Bspline(object):
    """
       Numpy implementation of Cox - de Boor algorithm in 1D

       inputs:
           knot_vector: Python list or Numpy array containing knot vector 
                        entries
           order: Order of interpolation, e.g. 0 -> piecewise constant between 
                  knots, 1 -> piecewise linear between knots, etc.
       outputs:
           basis object that is callable to evaluate basis functions at given 
           values of knot span
    """
    
    def __init__(self, knot_vector, order):
        """Initialize attributes"""
        self.knot_vector = np.array(knot_vector)
        self.p = order

        
    def __basis0(self, xi):
        """Order zero basis"""
        return np.where(np.all([self.knot_vector[:-1] <=  xi[:, np.newaxis], 
            xi[:,np.newaxis] < self.knot_vector[1:]],axis=0), 1.0, 0.0)
    
    def __basis(self, xi, p, compute_derivatives=False):
        """
           Recursive Cox - de Boor function to compute basis functions and 
           optionally their derivatives.
        """
        
        if p == 0:
            return self.__basis0(xi)
        else:
            basis_p_minus_1 = self.__basis(xi, p - 1)
        
        first_term_numerator = xi[:, np.newaxis] - self.knot_vector[:-p] 
        first_term_denominator = self.knot_vector[p:] - self.knot_vector[:-p]
        
        second_term_numerator = self.knot_vector[(p + 1):] - xi[:, np.newaxis]
        second_term_denominator = (self.knot_vector[(p + 1):] - 
                                   self.knot_vector[1:-p])
                
        
        #Change numerator in last recursion if derivatives are desired
        if compute_derivatives and p == self.p:
            
            first_term_numerator = np.ones((len(xi), 
                                            len(first_term_denominator))) * p
            second_term_numerator = np.ones((len(xi), 
                                             len(second_term_denominator))) * -p
            
        #Disable divide by zero error because we check for it
        with np.errstate(divide='ignore', invalid='ignore'):
            first_term = np.where(first_term_denominator != 0.0, 
                                  (first_term_numerator / 
                                   first_term_denominator), 0.0)
            second_term = np.where(second_term_denominator != 0.0,
                                   (second_term_numerator / 
                                    second_term_denominator), 0.0)

        return  (first_term[:,:-1] * basis_p_minus_1[:,:-1] + 
                 second_term * basis_p_minus_1[:,1:])
            
    
    def __call__(self, xi):
        """
           Convenience function to make the object callable.
        """
        return self.__basis(xi, self.p, compute_derivatives=False)
    
    def d(self, xi):
        """
           Convenience function to compute derivate of basis functions.  
        """
        return self.__basis(xi, self.p, compute_derivatives=True)
    
    def plot(self):
        """
           Convenience function to plot basis functions over full 
           range of knots.
        """
        
        x_min = np.min(self.knot_vector)
        x_max = np.max(self.knot_vector)
        
        x = np.linspace(x_min, x_max, num=1000, endpoint=False)
        
        N = self(x).T
        
        for n in N:
            
            plt.plot(x,n)
            
        return plt.show()

    
    def dplot(self):
        """
           Convenience function to plot derivatives of basis functions over 
           full range of knots.
        """
        
        x_min = np.min(self.knot_vector)
        x_max = np.max(self.knot_vector)
        
        x = np.linspace(x_min, x_max, num=1000, endpoint=False)
        
        N = self.d(x).T
        
        for n in N:
            
            plt.plot(x,n)
            
        return plt.show()
    

class NURBS_2D_Shape_Functions(Bspline):


    def __init__(self, knot_vector_1, p_1, knot_vector_2, p_2, weights):

        self.N = Bspline(knot_vector_1, p_1)
        self.M = Bspline(knot_vector_2, p_2)

        self.weights = weights


    def __call__(self, xi, eta, derivative=None):

        numerator = (np.einsum('...i,...j', self.N(xi), self.M(eta)) * 
                     self.weights)


        W = np.einsum('...i,...j,ij', self.N(xi), self.M(eta), self.weights)

        R = numerator / W[:, None, None]

        if derivative == 'xi':

            dW = np.einsum('...i,...j,ij', self.N.d(xi), self.M(eta), self.weights)

            R = (np.einsum('...i,...j', self.N.d(xi), self.M(eta)) * self.weights 
                 + dW[:, None, None] * R) / W[:, None, None]   

        if derivative == 'eta':

            dW = np.einsum('...i,...j,ij', self.N(xi), self.M.d(eta), self.weights)

            R = (np.einsum('...i,...j', self.N(xi), self.M.d(eta)) * self.weights 
                 + dW[:, None, None] * R) / W[:, None, None]   
        
        return R

    def d_xi(self, xi, eta):

        return self.__call__(xi, eta, derivative='xi')

    def d_eta(self, xi, eta):

        return self.__call__(xi, eta, derivative='eta')
                

    def plot(self, shape_function_number=0, derivative=None):

        xi_min = np.min(self.N.knot_vector)
        xi_max = np.max(self.N.knot_vector)

        eta_min = np.min(self.M.knot_vector)
        eta_max = np.max(self.M.knot_vector)

        xi = np.linspace(xi_min, xi_max, num=50, endpoint=False)
        eta = np.linspace(eta_min, eta_max, num=50, endpoint=False)

        x, y = np.meshgrid(xi, eta)

        basis = self(x.flatten(), y.flatten(), derivative)

        z = [basis[:,j,i].reshape(x.shape) for i in range(basis.shape[2]) for j in range(basis.shape[1])]

        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        surf = ax.plot_surface(x, y, z[shape_function_number], rstride=1, 
                               cstride=1, cmap=cm.coolwarm, linewidth=0, 
                               antialiased=False)
        fig.colorbar(surf, shrink=0.5, aspect=5)
        


class IGA2D(NURBS_2D_Shape_Functions):


    def __init__(self, knot_vector_1, p_1, knot_vector_2, p_2, 
                 control_points, weights):

        self.R = NURBS_2D_Shape_Functions(knot_vector_1, p_1, 
                                          knot_vector_2, p_2,
                                          weights)


        self.x = control_points[:,:,0].flatten()
        self.y = control_points[:,:,1].flatten()

        self.num_of_basis_functions_1 = (self.R.N.knot_vector.shape[0] - 
                                         self.R.N.p - 1)
        self.num_of_basis_functions_2 = (self.R.M.knot_vector.shape[0] - 
                                         self.R.M.p - 1)

        self.num_of_global_basis_functions = (self.num_of_basis_functions_1 *
                                              self.num_of_basis_functions_2)

        self.num_of_elements = ((self.num_of_basis_functions_1 - self.R.N.p) *
                                (self.num_of_basis_functions_2 - self.R.M.p))

        self.K = np.zeros((self.num_of_global_basis_functions, 
                           self.num_of_global_basis_functions))

        self.nurbs_coords = self.__build_nurbs_coord_array()

        self.connectivity_array = self.__build_connectivity_array()
   

    def __build_nurbs_coord_array(self):
        """
           Builds an array of coordinates in index space where each global basis
           function begins, the position in the array is the global basis id
        """

        #Index arrays in each basis direction
        i_arr = np.arange(self.num_of_basis_functions_1, dtype=np.int)
        j_arr = np.arange(self.num_of_basis_functions_2, dtype=np.int)

        #Construct the coordinate array
        return np.array([ (i, j) for j in j_arr for i in i_arr ], dtype=np.int)

    def __build_connectivity_array(self):
        """
           Builds an array that relates the local basis function #'s for each 
           element to the global basis function #'s.  Ordering starts with the 
           lower-left hand corner of an element in index space and moves 
           backwards starting in the xi direction, followed by the eta 
           direction row-by-row
        """

        #The total # of basis functions
        number_of_basis_functions = self.num_of_global_basis_functions

        #The global basis function id's
        global_basis_ids = np.arange(number_of_basis_functions, dtype=np.int)
        #Here we reshape the array to mimic the layout in basis index space, 
        #this makes finding the "lower left-hand" corner easier
        global_basis_ids.shape = (self.num_of_basis_functions_2,
                                  self.num_of_basis_functions_1)

        #i_arr and j_arr are convenience indices for iterating through the 
        #basis functions to determine the "lower left-hand" corner of the 
        #elements.  This procedure accounts for elements of zero measure due 
        #to possibly open knot vectors.
        i_arr = np.arange(self.R.N.p, self.num_of_basis_functions_1, dtype=np.int)
        j_arr = np.arange(self.R.M.p, self.num_of_basis_functions_2, dtype=np.int)
        
        #Array of element corner indices pairs, i.e. (i,j)
        elem_corner = [(i,j) for j in j_arr for i in i_arr]

        #Constructs the connectivity array.  This does a slice from the element
        #corner location (i,j), backwards by p_1 in the \xi direction and p_2
        #in the \eta direction to get all basis functions that have support on
        #each element. The it flatten's the matrix to make an array and reverses 
        #the order with the [::-1] to be consistent with the convention that
        #the arrays start with the corner basis id and move backwards in \xi
        #and \eta.  Excuse the 
        return  np.array([(global_basis_ids[(j-self.R.M.p):(j+1),(i-self.R.N.p):(i+1)].flatten())[::-1] 
            for i,j in elem_corner])
        

    def __compute_element_stiffness(self):
        """
           Computes the element stiffness matrix
        """

        con = self.connectivity_array
        number_of_basis_functions = self.num_of_global_basis_functions
        number_of_elements = self.num_of_elements
        
        #The knot indices cooresponding to the nurbs coordinates 
        #where elements begin
        ni = self.nurbs_coords[con[:,0],0]
        nj = self.nurbs_coords[con[:,0],1]

        #Compute the Gauss quadrature points to integrate each shape function
        #to full order
        xi_, wt_xi_ = compute_gauss_points_and_weights(self.R.N.p + 1)
        eta_, wt_eta_ = compute_gauss_points_and_weights(self.R.M.p + 1)

        #Create all the quadrature point tuples
        xi, eta = np.meshgrid(xi_, eta_)
        wt_xi, wt_eta = np.meshgrid(wt_xi_, wt_eta_)

        #Flatten arrays containing quadrature points and weights
        xi = xi.flatten()
        eta = eta.flatten()
        wt_xi = wt_xi.flatten()
        wt_eta = wt_eta.flatten()

        #Takes Gauss integration points into parameter space, has structure
        #xi_1 -> xi_1_el1, xi_1_el2, xi_1_el3, ...
        #xi_2 -> xi_2_el1, xi_2_el2, xi_2_el3, ...
        #flattened into one long array
        xi = (((self.R.N.knot_vector[ni+1] - self.R.N.knot_vector[ni]) * xi[:, np.newaxis] + 
              (self.R.N.knot_vector[ni+1] + self.R.N.knot_vector[ni])) / 2.0).flatten()

        eta = (((self.R.M.knot_vector[nj+1] - self.R.M.knot_vector[nj]) * eta[:, np.newaxis] + 
               (self.R.M.knot_vector[nj+1] + self.R.M.knot_vector[nj])) / 2.0).flatten()

        #Evaluate basis functions. 1st axis is the # of Gauss integration points, 2nd
        #axis is # of elements, 3rd is values of shape functions
        dRdxi = self.R.d_xi(xi, eta).reshape(-1, number_of_elements, number_of_basis_functions)
        dRdeta = self.R.d_eta(xi, eta).reshape(-1, number_of_elements, number_of_basis_functions)
        print self.R.d_xi(xi, eta)

        #Store only the shape function values with support on an element
        #shape=(# Gauss points, # of elements, # of nonzero values of shape functions)
        dRdxi = dRdxi[:, np.arange(con.shape[0])[:, np.newaxis], con]
        dRdeta = dRdeta[:, np.arange(con.shape[0])[:, np.newaxis], con]

        #These are dot products, x = x_i . R_i, broadcast to every integration point
        #shape = (# Gauss points, # of elements)
        J11 = np.sum(self.x[con] * dRdxi, axis=2)
        J12 = np.sum(self.x[con] * dRdeta, axis=2)
        J21 = np.sum(self.y[con] * dRdxi, axis=2)
        J22 = np.sum(self.y[con] * dRdeta, axis=2)
        
        #Compute the determinate of J and inverse
        detJ = J11 * J22 - J12 * J21

        
        Jinv11 =  J22 / detJ
        Jinv12 = -J12 / detJ
        Jinv21 = -J21 / detJ
        Jinv22 =  J11 / detJ

        #Gradient of mapping between Gauss coords and parametric coords
        dxidxi = (self.R.N.knot_vector[ni+1] - self.R.N.knot_vector[ni]) / 2.0
        detadeta = (self.R.M.knot_vector[nj+1] - self.R.M.knot_vector[nj]) / 2.0

        #Jacobian determinate of mapping from physical to Gauss coords.
        #Uses the fact that det(A*B) = det(A) * deta(B) and 
        #det(B) is product along diagonal for a diagonal matrix
        #
        #Also multiply the quadrature weights in at this point
        detJ = detJ * dxidxi * detadeta * wt_xi * wt_eta

        #The shape functions in physical coordinates
        self.dRdx = (dRdxi * Jinv11[:, np.arange(Jinv11.shape[0]), np.newaxis] +
                     dRdeta * Jinv12[:, np.arange(Jinv12.shape[0]), np.newaxis])

        self.dRdy = (dRdxi * Jinv21[:, np.arange(Jinv21.shape[0]), np.newaxis] +
                     dRdeta * Jinv22[:, np.arange(Jinv22.shape[0]), np.newaxis])
         
        #The element stiffness matrices.
        return np.sum((np.einsum('...i,...j', self.dRdx, self.dRdx) + 
                     np.einsum('...i,...j', self.dRdy, self.dRdy)) * 
                     detJ, axis=0)


    def assemble(self):

        ke = self.__compute_element_stiffness()

        for i in range(self.num_of_elements):

            idx_grid = np.ix_(self.connectivity_array[i], 
                              self.connectivity_array[i])
            self.K[idx_grid]  += ke[i]

    def apply_bcs(self, nodes, values):

        row_replace = np.zeros(self.num_of_elements)

        for value_idx, node in enumerate(nodes):

            self.K[node] = row_replace
            self.K[node, node] = 1

            self.F[node] = values[value_idx]


    def solve(self):

        self.K = scipy.sparse.csr_matrix(self.K)

        return scipy.sparse.linalg.spsolve(self.K, self.F)


        
