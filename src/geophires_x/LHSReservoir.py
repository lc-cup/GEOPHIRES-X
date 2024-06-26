import sys
# import os
import math
import numpy as np
from mpmath import *
import geophires_x.Model as Model
from .Reservoir import Reservoir


class LHSReservoir(Reservoir):
    """
    This class models the Linear Heat Sweep Reservoir.  It is a subclass of the Reservoir class.
    It inherits all the methods and attributes of those classes, and can override them as necessary.
    It also has its own methods and attributes that are unique to this class.
    """

    def __init__(self, model: Model):
        """
        The __init__ function is called automatically when a class is instantiated.
        It initializes the attributes of an object, and sets default values for certain arguments that can be overridden by user input.
        Set up all the Parameters that will be predefined by this class using the different types of parameter classes.
        Setting up includes giving it a name, a default value, The Unit Type (length, volume, temperature, etc)
        and Unit Name of that value, sets it as required (or not), sets allowable range, the error message
        if that range is exceeded, the ToolTip Text, and the name of teh class that created it.
        This includes setting up temporary variables that will be available to all the class
        but noy read in by user, or used for Output
        This also includes all Parameters that are calculated and then published using the Printouts function.
        If you choose to subclass this master class, you can do so before or after you create your own parameters.
        If you do, you can also choose to call this method from you class,
        which will effectively add and set all these parameters to your class.
        :param model: The container class of the application, giving access to everything else, including the logger
        :type model: :class:`~geophires_x.Model.Model`
        :return: None
        """
        model.logger.info(f'Init {__class__!s}: {sys._getframe().f_code.co_name}')
        super().__init__(model)  # initialize the parent parameters and variables
        sclass = str(__class__).replace("<class \'", "")
        self.myClass = sclass.replace("\'>", "")
        model.logger.info(f'Complete {__class__!s}: {sys._getframe().f_code.co_name}')

    def __str__(self):
        return 'LHSReservoir'

    def read_parameters(self, model: Model) -> None:
        """
        The read_parameters function reads in the parameters from a dictionary created by reading the user-provided file
         and updates the parameter values for this object.
        The function reads in all the parameters that relate to this object, including those that are inherited
        from other objects. It then updates any of these parameter values that have been changed by the user.
          It also handles any special cases.
        :param model: The container class of the application, giving access to everything else, including the logger
        :type model: :class:`~geophires_x.Model.Model`
        :return: None
        """
        model.logger.info(f'Init {__class__!s}: {sys._getframe().f_code.co_name}')

        # if we call super, we don't need to deal with setting the parameters here,
        # just deal with the special cases for the variables in this class
        # because the call to the super.readparameters will set all the variables,
        # including the ones that are specific to this class
        super().read_parameters(model)  # read the parameters for the parent.

        model.logger.info(f'Complete {__class__!s}: {sys._getframe().f_code.co_name}')

    def Calculate(self, model: Model):
        """
        The Calculate function calculates the values of all the parameters that are calculated by this object.
        It calls the Calculate function of the parent object to calculate the values of the parameters that are
        calculated by the parent object.
        It then calculates the values of the parameters that are calculated by this object.
        :param model: The container class of the application, giving access to everything else, including the logger
        :type model: :class:`~geophires_x.Model.Model`
        :return: None
        """
        model.logger.info(f'Init {__class__!s}: {sys._getframe().f_code.co_name}')
        super().Calculate(model)  # run calculate for the parent.

        # specify rock properties
        phi = model.reserv.porrock.value  # porosity [%]
        h = 500.  # heat transfer coefficient [W/m^2 K]
        shape = 0.2  # ratio of conduction path length
        alpha = model.reserv.krock.value / (model.reserv.rhorock.value * model.reserv.cprock.value)

        # storage ratio
        gamma = (model.reserv.rhowater.value * model.reserv.cpwater.value * phi) / (
                model.reserv.rhorock.value * model.reserv.cprock.value * (1 - phi))

        # effective rock radius
        r_efr = 0.83 * (0.75 * (model.reserv.fracsepcalc.value * model.reserv.fracheightcalc.value * model.reserv.fracwidthcalc.value) / math.pi) ** (1. / 3.)

        # Biot number
        Bi = h * r_efr / model.reserv.krock.value

        # effective rock time constant
        tau_efr = r_efr ** 2. * (shape + 1. / Bi) / (3. * alpha)

        # reservoir dimensions and flow properties
        hl = (model.reserv.fracnumbcalc.value - 1) * model.reserv.fracsepcalc.value
        wl = model.reserv.fracwidthcalc.value
        aave = hl * wl
        u0 = model.wellbores.nprod.value * model.wellbores.prodwellflowrate.value / (model.reserv.rhowater.value * aave)
        tres = (model.reserv.fracheightcalc.value * phi) / u0

        # number of heat transfer units
        ntu = tres / tau_efr

        # specify Laplace-space function
        fp = lambda s: (1 / s) * (1 - exp(-(1 + ntu / (gamma * (s + ntu))) * s))

        # calculate non-dimensional temperature array
        Twnd = []
        try:
            for t in range(1, len(model.reserv.timevector.value)):
                Twnd = Twnd + [float(
                    invertlaplace(fp, model.reserv.timevector.value[t] * 365. * 24. * 3600. / tres, method='talbot'))]
        except:
            raise RuntimeError('Error: GEOPHIRES could not execute numerical inverse laplace calculation for '
                               'reservoir model 2. '
                               'Simulation will abort.')

        Twnd = np.asarray(Twnd)

        # calculate dimensional temperature, add error-handling for nonsensical temperatures
        model.reserv.Tresoutput.value = Twnd * (
                model.reserv.Trock.value - model.wellbores.Tinj.value) + model.wellbores.Tinj.value
        model.reserv.Tresoutput.value = np.append([model.reserv.Trock.value], model.reserv.Tresoutput.value)
        model.reserv.Tresoutput.value = np.asarray([model.reserv.Trock.value if x > model.reserv.Trock.value or x < model.wellbores.Tinj.value else x for x in model.reserv.Tresoutput.value])

        model.logger.info(f'Complete {__class__!s}: {sys._getframe().f_code.co_name}')
