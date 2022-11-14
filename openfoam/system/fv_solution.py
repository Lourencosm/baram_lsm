#!/usr/bin/env python
# -*- coding: utf-8 -*-
from builtins import str

from coredb import coredb
from coredb.numerical_db import NumericalDB, PressureVelocityCouplingScheme
from coredb.general_db import GeneralDB
from coredb.region_db import RegionDB
from coredb.material_db import Phase
from coredb.models_db import ModelsDB
from coredb.reference_values_db import ReferenceValuesDB
from openfoam.dictionary_file import DictionaryFile


class FvSolution(DictionaryFile):
    def __init__(self, rname: str = None):
        super().__init__(self.systemLocation(rname), 'fvSolution')

        self._rname = rname
        self._db = coredb.CoreDB()

    def build(self):
        if self._data is not None:
            return self

        if self._rname is None:
            # Global fvSolution in multi region case
            self._data = {
                'PIMPLE': {
                    'nOuterCorrectors':
                        self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/maxIterationsPerTimeStep'),
                }

            }
        else:
            # If region name is empty string, the only fvSolution in single region case.
            # Otherwise, fvSolution of specified region.
            scheme = self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/pressureVelocityCouplingScheme')
            phase = RegionDB.getPhase(self._rname)
            consistent = 'no'
            momentumPredictor = 'on'
            energyOn = ModelsDB.isEnergyModelOn()

            if scheme == PressureVelocityCouplingScheme.SIMPLEC.value and phase != Phase.SOLID:
                consistent = 'yes'
            if self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/useMomentumPredictor') == 'false':
                momentumPredictor = 'off'

            self._data = {
                'solvers': {
                    '"(p|pcorr)"': (p := self._constructSolversP()),
                    '"(p|pcorr)Final"': p,
                    'p_rgh': (p_rgh := {
                        'solver': 'PCG',
                        'preconditioner': {
                            'preconditioner': 'GAMG',
                            'smoother': 'DIC',
                            'tolerance': '1e-5',
                            'relTol': '0.1',
                        },
                        'tolerance': '1e-16',
                        'relTol': '0.1',
                        'minIter': '1',
                        'maxIter': '5',
                    }),
                    'p_rghFinal': p_rgh,
                    'h': (h := self._constructSolversH(phase)),
                    'hFinal': h,
                    'rho': (rho := {
                        'solver': 'PCG',
                        'preconditioner': 'DIC',
                        'tolerance': '1e-16',
                        'relTol': '0.1',
                        'minIter': '1',
                        'maxIter': '5',
                    }),
                    'rhoFinal': rho,
                    '"(U|k|epsilon|omega|nuTilda)"': (others := {
                        'solver': 'PBiCGStab',
                        'preconditioner': 'DILU',
                        'tolerance': '1e-16',
                        'relTol': '0.1',
                        'minIter': '1',
                        'maxIter': '5',
                    }),
                    '"(U|k|epsilon|omega|nuTilda)Final"': others
                },
                'SIMPLE': {
                    'consistent': consistent,
                    'nNonOrthogonalCorrectors': '0',
                    # only for fluid
                    'pRefPoint': self._db.getVector(
                        ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/referencePressureLocation'),
                    # only for fluid
                    'pRefValue': self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/pressure'),
                    'solveEnergy': 'yes' if energyOn else 'no',  # NEXTfoam custom option
                    'residualControl': {
                        'p': self._db.getValue('.//convergenceCriteria/pressure/absolute'),
                        'p_rgh': self._db.getValue('//convergenceCriteria/pressure/absolute'),
                        'U': self._db.getValue('//convergenceCriteria/momentum/absolute'),
                        'h': self._db.getValue('//convergenceCriteria/energy/absolute'),
                        '"(k|epsilon|omega|nuTilda)"': self._db.getValue('//convergenceCriteria/turbulence/absolute'),
                    }
                },
                'PIMPLE': {
                    'consistent': consistent,
                    'momentumPredictor': momentumPredictor,
                    # only for fluid
                    'turbOnFinalIterOnly': 'false',
                    'nNonOrthogonalCorrectors': '0',
                    # only for fluid
                    'nCorrectors': self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/numberOfCorrectors'),
                    # only in single region case
                    'nOuterCorrectors':
                        self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/maxIterationsPerTimeStep'),
                    'maxCo': self._db.getValue('.//runConditions/maxCourantNumber'),
                    'nonOrthogonalityThreshold': '80',
                    'skewnessThreshold': '0.95',
                    # only for fluid
                    'pRefPoint': self._db.getVector(
                        ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/referencePressureLocation'),
                    # only for fluid
                    'pRefValue': self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/pressure'),
                    'rDeltaTSmoothingCoeff': '0.05',
                    'rDeltaTDampingCoeff': '0.5',
                    'solveEnergy': 'yes' if energyOn else 'no',  # NEXTfoam custom option
                    'residualControl': {
                        'p': {
                            'tolerance': self._db.getValue('.//convergenceCriteria/pressure/absolute'),
                            'relTol': self._db.getValue('.//convergenceCriteria/pressure/relative'),
                        },
                        'p_rgh': {
                            'tolerance': self._db.getValue('.//convergenceCriteria/pressure/absolute'),
                            'relTol': self._db.getValue('.//convergenceCriteria/pressure/relative'),
                        },
                        'U': {
                            'tolerance': self._db.getValue('.//convergenceCriteria/momentum/absolute'),
                            'relTol': self._db.getValue('.//convergenceCriteria/momentum/relative'),
                        },
                        'h': {
                            'tolerance': self._db.getValue('.//convergenceCriteria/energy/absolute'),
                            'relTol': self._db.getValue('.//convergenceCriteria/energy/relative'),
                        },
                        '"(k|epsilon|omega|nuTilda)"': {
                            'tolerance': self._db.getValue('.//convergenceCriteria/turbulence/absolute'),
                            'relTol': self._db.getValue('.//convergenceCriteria/turbulence/relative'),
                        },
                    }
                },
                'relaxationFactors': {
                    'fields': {
                        'p': self._db.getValue('.//underRelaxationFactors/pressure'),
                        'pFinal': self._db.getValue('.//underRelaxationFactors/pressureFinal'),
                        'p_rgh': self._db.getValue('.//underRelaxationFactors/pressure'),
                        'p_rghFinal': self._db.getValue('.//underRelaxationFactors/pressureFinal'),
                        'rho': self._db.getValue('.//underRelaxationFactors/density'),
                        'rhoFinal': self._db.getValue('.//underRelaxationFactors/densityFinal'),
                    },
                    'equations': {
                        'U': self._db.getValue('.//underRelaxationFactors/momentum'),
                        'UFinal': self._db.getValue('.//underRelaxationFactors/momentumFinal'),
                        'h': self._db.getValue('.//underRelaxationFactors/energy'),
                        'hFinal': self._db.getValue('.//underRelaxationFactors/energyFinal'),
                        '"(k|epsilon|omega|nuTilda)"': self._db.getValue('.//underRelaxationFactors/turbulence'),
                        '"(k|epsilon|omega|nuTilda)Final"': self._db.getValue('.//underRelaxationFactors/turbulenceFinal'),
                    }
                }
            }

        return self

    def _constructSolversP(self):
        if GeneralDB.isCompressible():
            return {
                'solver': 'PBiCGStab',
                'preconditioner': 'DILU',
                'tolerance': '1e-16',
                'relTol': '0.1',
                'minIter': '1',
                'maxIter': '5',
            }
        else:
            return {
                'solver': 'PCG',
                'preconditioner': {
                    'preconditioner': 'GAMG',
                    'smoother': 'DIC',
                    'tolerance': '1e-5',
                    'relTol': '0.1',
                },
                'tolerance': '1e-16',
                'relTol': '0.1',
                'minIter': '1',
                'maxIter': '5',
            }

    def _constructSolversH(self, phase):
        if phase == Phase.SOLID:
            return {
                'solver': 'PBiCGStab',
                'preconditioner': {
                    'preconditioner': 'GAMG',
                    'smoother': 'DIC',
                    'tolerance': '1e-5',
                    'relTol': '0.1',
                },
                'tolerance': '1e-16',
                'relTol': '0.1',
                'minIter': '1',
                'maxIter': '5',
            }
        else:
            return {
                'solver': 'PBiCGStab',
                'preconditioner': {
                    'preconditioner': 'GAMG',
                    'smoother': 'DILU',
                    'tolerance': '1e-5',
                    'relTol': '0.1',
                },
                'tolerance': '1e-16',
                'relTol': '0.1',
                'minIter': '1',
                'maxIter': '5',
            }
