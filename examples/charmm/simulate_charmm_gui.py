#!/usr/bin/env python
from __future__ import division, print_function

import sys

# OpenMM Imports
import simtk.unit as u
import simtk.openmm as mm
import simtk.openmm.app as app

# ParmEd Imports
from chemistry.charmm.openmmloader import (OpenMMCharmmPsfFile as CharmmPsfFile,
                                           OpenMMCharmmCrdFile as CharmmCrdFile)
from chemistry.charmm.parameters import CharmmParameterSet
from chemistry.amber.openmmreporters import (
            AmberStateDataReporter as AKMAStateDataReporter)

# Load the CHARMM files
print('Loading CHARMM files...')
params = CharmmParameterSet('toppar/par_all36_prot.prm',
                            'toppar/toppar_water_ions.str')
ala2_solv = CharmmPsfFile('ala2_charmmgui.psf')
ala2_crds = CharmmCrdFile('ala2_charmmgui.crd')

# Compute the box dimensions from the coordinates and set the box lengths (only
# orthorhombic boxes are currently supported in OpenMM)
coords = ala2_crds.positions
min_crds = [coords[0][0], coords[0][1], coords[0][2]]
max_crds = [coords[0][0], coords[0][1], coords[0][2]]

for coord in coords:
    min_crds[0] = min(min_crds[0], coord[0])
    min_crds[1] = min(min_crds[1], coord[1])
    min_crds[2] = min(min_crds[2], coord[2])
    max_crds[0] = max(max_crds[0], coord[0])
    max_crds[1] = max(max_crds[1], coord[1])
    max_crds[2] = max(max_crds[2], coord[2])

ala2_solv.setBox(max_crds[0]-min_crds[0],
                 max_crds[1]-min_crds[1],
                 max_crds[2]-min_crds[2],
)

# Create the OpenMM system
print('Creating OpenMM System')
system = ala2_solv.createSystem(params, nonbondedMethod=app.PME,
                                nonbondedCutoff=6.0*u.angstroms,
                                constraints=app.HBonds,
)

# Create the integrator to do Langevin dynamics
integrator = mm.LangevinIntegrator(
                        300*u.kelvin,       # Temperature of heat bath
                        1.0/u.picoseconds,  # Friction coefficient
                        2.0*u.femtoseconds, # Time step
)

# Define the platform to use; CUDA, OpenCL, CPU, or Reference. Or do not specify
# the platform to use the default (fastest) platform
platform = mm.Platform.getPlatformByName('CUDA')
prop = dict(CudaPrecision='mixed') # Use mixed single/double precision

# Create the Simulation object
sim = app.Simulation(ala2_solv.topology, system, integrator, platform, prop)

# Set the particle positions
sim.context.setPositions(ala2_crds.positions)

# Minimize the energy
print('Minimizing energy')
sim.minimizeEnergy(maxIterations=500)

# Set up the reporters to report energies and coordinates every 100 steps
sim.reporters.append(
        AKMAStateDataReporter(sys.stdout, 100, step=True, potentialEnergy=True,
                              kineticEnergy=True, temperature=True,
                              volume=True, density=True)
)
sim.reporters.append(app.DCDReporter('ala2_solv.dcd', 100))

# Run dynamics
print('Running dynamics')
sim.step(10000)