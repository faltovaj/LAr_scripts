from Configurables import ApplicationMgr
from Configurables import PodioOutput
from Configurables import AuditorSvc, ChronoAuditor
from Configurables import EnergyInCaloLayers
from Configurables import CreateCaloCells
from Configurables import SimG4PrimariesFromEdmTool
from Configurables import SimG4Alg, SimG4SaveCalHits
from Configurables import SimG4Svc
from os import environ, path
from Configurables import GeoSvc
from Configurables import HepMCToEDMConverter
from Configurables import GenAlg
from Configurables import MomentumRangeParticleGun
from Configurables import FCCDataSvc
from Gaudi.Configuration import WARNING, INFO

from GaudiKernel.SystemOfUnits import GeV

# Electron momentum in GeV
momentum = 50
# Theta min and max in degrees
thetaMin = 85.
thetaMax = 95.

# Data service
podioevent = FCCDataSvc("EventDataSvc")

# Particle gun setup
_pi = 3.14159

pgun = MomentumRangeParticleGun("ParticleGun_Electron")
pgun.PdgCodes = [11]
pgun.MomentumMin = momentum * GeV
pgun.MomentumMax = momentum * GeV
pgun.PhiMin = 0
pgun.PhiMax = 2 * _pi
# theta = 90 degrees (eta = 0)
pgun.ThetaMin = thetaMin * _pi / 180.
pgun.ThetaMax = thetaMax * _pi / 180.

genalg_pgun = GenAlg()
genalg_pgun.SignalProvider = pgun
genalg_pgun.hepmc.Path = "hepmc"

hepmc_converter = HepMCToEDMConverter()
hepmc_converter.hepmc.Path = "hepmc"
hepmc_converter.GenParticles.Path = "GenParticles"

# DD4hep geometry service
geoservice = GeoSvc("GeoSvc",
                    OutputLevel=WARNING)
path_to_detector = environ.get("K4GEO", "")
detectors_to_use = [
    'FCCee/ALLEGRO/compact/ALLEGRO_o1_v03/DectEmptyMaster.xml',
    'FCCee/ALLEGRO/compact/ALLEGRO_o1_v03/ECalBarrel_thetamodulemerged_upstream.xml'
]
geoservice.detectors = [path.join(
    path_to_detector, _det) for _det in detectors_to_use]

# Geant4 service
# Configures the Geant simulation: geometry, physics list and user actions
geantservice = SimG4Svc("SimG4Svc", detector='SimG4DD4hepDetector',
                        physicslist="SimG4FtfpBert", actions="SimG4FullSimActions")
geantservice.g4PostInitCommands += ["/run/setCut 0.1 mm"]

# Fixed seed to have reproducible results, change it for each job if you split one production into several jobs
# Mind that if you leave Gaudi handle random seed and some job start within the same second (very likely) you will have duplicates
geantservice.randomNumbersFromGaudi = False
geantservice.seedValue = 4242

# Geant4 algorithm
# Translates EDM to G4Event, passes the event to G4, writes out outputs via tools
# and a tool that saves the calorimeter hits
saveecaltool = SimG4SaveCalHits(
    "saveECalBarrelHits", readoutName="ECalBarrelModuleThetaMerged")
saveecaltool.CaloHits.Path = "ECalBarrelHits"

particle_converter = SimG4PrimariesFromEdmTool("EdmConverter")
particle_converter.GenParticles.Path = "GenParticles"

# next, create the G4 algorithm, giving the list of names of tools ("XX/YY")
geantsim = SimG4Alg("SimG4Alg",
                    outputs=["SimG4SaveCalHits/saveECalBarrelHits"],
                    eventProvider=particle_converter,
                    OutputLevel=INFO)

createcellsBarrel = CreateCaloCells("CreateCaloCellsBarrel",
                                    doCellCalibration=False,
                                    addPosition=True,
                                    addCellNoise=False, filterCellNoise=False)
createcellsBarrel.hits.Path = "ECalBarrelHits"
createcellsBarrel.cells.Path = "ECalBarrelCells"

energy_in_layers = EnergyInCaloLayers("energyInLayers",
                                      readoutName="ECalBarrelModuleThetaMerged",
                                      numLayers=11,
                                      # sampling fraction is given as the energy correction will be applied on
                                      # calibrated cells
                                      # do not split the following line on multiple lines or it will break scripts
                                      # that update the values of the corrections
                                      samplingFractions = [0.3816106371465399] * 1 + [0.13606027272993534] * 1 + [0.14440377278980568] * 1 + [0.1498462792215245] * 1 + [0.15488829608278676] * 1 + [0.1592259999853961] * 1 + [0.1642734994350156] * 1 + [0.16801026142777753] * 1 + [0.17010820066138732] * 1 + [0.1770417190969021] * 1 + [0.17898793052964337] * 1,
                                      OutputLevel=INFO)
energy_in_layers.deposits.Path = "ECalBarrelCells"
energy_in_layers.particle.Path = "GenParticles"

# CPU information
chra = ChronoAuditor()
audsvc = AuditorSvc()
audsvc.Auditors = [chra]
geantsim.AuditExecute = True
# energy_in_layers.AuditExecute = True

# PODIO algorithm
out = PodioOutput("out", OutputLevel=INFO)
out.outputCommands = ["keep *", "drop ECalBarrelCells", "drop ECalBarrelHits"]
out.filename = "fccee_deadMaterial_inclinedEcal.root"

# ApplicationMgr
ApplicationMgr(TopAlg=[genalg_pgun, hepmc_converter, geantsim, createcellsBarrel, energy_in_layers, out],
               EvtSel='NONE',
               EvtMax=10,
               # order is important, as GeoSvc is needed by G4SimSvc
               ExtSvc=[geoservice, podioevent, geantservice, audsvc],
               OutputLevel=INFO
               )
