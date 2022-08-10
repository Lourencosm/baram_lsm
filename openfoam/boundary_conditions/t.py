#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from coredb.filedb import BcFileRole
from coredb.boundary_db import BoundaryDB, BoundaryType, FlowRateInletSpecification
from coredb.boundary_db import TemperatureProfile, TemperatureTemporalDistribution, InterfaceMode
from coredb.cell_zone_db import RegionDB
from coredb.material_db import Phase
from coredb.project import Project
from openfoam.boundary_conditions.boundary_condition import BoundaryCondition


class T(BoundaryCondition):
    DIMENSIONS = '[0 0 0 1 0 0 0]'

    def __init__(self, rname: str):
        super().__init__(self.boundaryLocation(rname), 'T')

        self._rname = rname
        self._db = coredb.CoreDB()
        self._initialValue = self._db.getValue('.//initialization/initialValues/temperature')

    def build(self):
        if self._data is not None:
            return self

        self._data = {
            'dimensions': self.DIMENSIONS,
            'internalField': ('uniform', self._initialValue),
            'boundaryField': self._constructBoundaryField()
        }

        return self

    def _constructBoundaryField(self):
        field = {}

        boundaries = self._db.getBoundaryConditions(self._rname)
        for bcid, name, type_ in boundaries:
            xpath = BoundaryDB.getXPath(bcid)

            profile = self._db.getValue(xpath + '/temperature/profile')
            if profile == TemperatureProfile.CONSTANT.value:
                constant = self._db.getValue(xpath + '/temperature/constant')

                field[name] = {
                    BoundaryType.VELOCITY_INLET.value:      (lambda: self._constructFixedValue(constant)),
                    BoundaryType.FLOW_RATE_INLET.value:     (lambda: self._constructFlowRateInletT(xpath, constant)),
                    BoundaryType.PRESSURE_INLET.value:      (lambda: self._constructInletOutletTemperature(constant)),
                    BoundaryType.PRESSURE_OUTLET.value:     (lambda: self._constructPressureOutletT(xpath, constant)),
                    BoundaryType.ABL_INLET.value:           (lambda: None),
                    BoundaryType.OPEN_CHANNEL_INLET.value:  (lambda: None),
                    BoundaryType.OPEN_CHANNEL_OUTLET.value: (lambda: None),
                    BoundaryType.OUTFLOW.value:             (lambda: self._constructZeroGradient()),
                    BoundaryType.FREE_STREAM.value:         (lambda: self._constructFreestream(xpath + '/freeStream')),
                    BoundaryType.FAR_FIELD_RIEMANN.value:   (lambda: self._constructFarfieldRiemann(xpath + '/farFieldRiemann')),
                    BoundaryType.SUBSONIC_INFLOW.value:     (lambda: self._constructSubsonicInflow(xpath + '/subsonicInflow')),
                    BoundaryType.SUBSONIC_OUTFLOW.value:    (lambda: self._constructSubsonicOutflow(xpath + '/subsonicOutflow')),
                    BoundaryType.SUPERSONIC_INFLOW.value:   (lambda: self._constructFixedValue(constant)),
                    BoundaryType.SUPERSONIC_OUTFLOW.value:  (lambda: self._constructZeroGradient()),
                    BoundaryType.WALL.value:                (lambda: self._constructZeroGradient()),
                    BoundaryType.THERMO_COUPLED_WALL.value: (lambda: self._constructNEXTTurbulentTemperatureCoupledBaffleMixed()),
                    BoundaryType.SYMMETRY.value:            (lambda: self._constructSymmetry()),
                    BoundaryType.INTERFACE.value:           (lambda: self._constructInterfaceT(xpath)),
                    BoundaryType.POROUS_JUMP.value:         (lambda: self._constructPorousBafflePressure(xpath + '/porousJump')),
                    BoundaryType.FAN.value:                 (lambda: self._constructCyclic()),
                    BoundaryType.EMPTY.value:               (lambda: self._constructEmpty()),
                    BoundaryType.CYCLIC.value:              (lambda: self._constructCyclic()),
                    BoundaryType.WEDGE.value:               (lambda: self._constructWedge()),
                }.get(type_)()
            elif profile == TemperatureProfile.SPATIAL_DISTRIBUTION.value:
                field[name] = self._constructTimeVaryingMappedFixedValue(
                    self._rname, name, 'T', Project.instance().fileDB().getBcFile(bcid, BcFileRole.BC_TEMPERATURE))
            elif profile == TemperatureProfile.TEMPORAL_DISTRIBUTION.value:
                spec = self._db.getValue(xpath + '/temperature/temporalDistribution/specification')
                if spec == TemperatureTemporalDistribution.PIECEWISE_LINEAR.value:
                    field[name] = self._constructUniformFixedValue(
                        xpath + '/temperature/temporalDistribution/piecewiseLinear', self.TableType.TEMPORAL_SCALAR_LIST
                    )
                elif spec == TemperatureTemporalDistribution.POLYNOMIAL.value:
                    field[name] = self._constructUniformFixedValue(
                        xpath + '/temperature/temporalDistribution/polynomial', self.TableType.POLYNOMIAL)

        return field

    def _constructInletOutletTemperature(self, constant):
        return {
            'type': 'inletOutletTotalTemperature',
            'gamma': 'gamma',
            'inletValue': ('uniform', constant),
            'T0': ('uniform', constant)
        }

    def _constructNEXTTurbulentTemperatureCoupledBaffleMixed(self):
        return {
            'type': 'turbulentTemperatureCoupledBaffleMixed',
            'Tnbr': 'T',
            'kappaMethod': 'solidThermo' if RegionDB.getPhase(self._rname) == Phase.SOLID else 'fluidThermo'
        }

    def _constructFlowRateInletT(self, xpath, constant):
        spec = self._db.getValue(xpath + '/flowRateInlet/flowRate/specification')
        if spec == FlowRateInletSpecification.VOLUME_FLOW_RATE.value:
            return self._constructFixedValue(constant)
        elif spec == FlowRateInletSpecification.MASS_FLOW_RATE.value:
            return self._constructInletOutletTemperature(constant)

    def _constructPressureOutletT(self, xpath, constant):
        if self._db.getValue(xpath + '/pressureOutlet/calculatedBackflow') == 'true':
            return self._constructInletOutletTemperature(constant)
        else:
            return self._constructZeroGradient()

    def _constructInterfaceT(self, xpath):
        spec = self._db.getValue(xpath + '/interface/mode')
        if spec == InterfaceMode.REGION_INTERFACE.value:
            return self._constructNEXTTurbulentTemperatureCoupledBaffleMixed()
        else:
            return self._constructCyclicAMI()
