"""
Python module to clean up and generate files used with Xpedite pytests.
This module generates baseline profile information and probe state information.
Baseline information for profiles is created by generating a Jupyter notebook
for a new Xpedite run, and copying over the .xpd profile information file and
.data files from the xpedite run to the pytest data directory.

Author:  Brooke Elizabeth Cantwell, Morgan Stanley
"""

import os
from shutil                               import copy, rmtree
import logging
import logging.config
from logger                               import LOG_CONFIG_PATH
from test_xpedite.test_profiler.profile   import (
                                            buildNotebook, loadProfileInfo, loadProbes,
                                          )

logging.config.fileConfig(LOG_CONFIG_PATH)
LOGGER = logging.getLogger('xpedite')

def replaceWorkspace(filePath, workspace, destination):
  with open(filePath, 'r') as fileHandle:
    appInfoStr = fileHandle.read()

  appInfoStr = appInfoStr.replace(workspace, '')

  with open(destination, 'w') as fileHandle:
    fileHandle.write(appInfoStr)

def cleanUpDataDir(tempDir, appName):
  """
  Old data files need to be removed before creating new files
  """
  import glob
  dataDir = os.path.join(os.path.dirname(__file__), '..', 'data')
  os.remove(os.path.join(dataDir, '{}.tar.gz'.format(appName)))
  for dataFile in glob.glob(os.path.join(tempDir, '*.data')):
    os.remove(dataFile)
  if os.path.isdir(os.path.join(tempDir, 'benchmark')):
    rmtree(os.path.join(tempDir, 'benchmark'))

def generateBaseline(binary, tempDir, workspace, appName):
  """
  Generate the following files:
  1. .xpd data file generated from building a Jupyter notebook
     Used to test building of notebooks
  2. Xpedite application information file
     Used to attach profiler for testing recording, reporting, probe status, and notebooks
  3. xpediteDemo .data files
     Files that are collected by an xpedite app to build transactions
  4. Serialized probe baseline file
     Used to compare probe states generated by an xpedite app to baseline probes
  """
  import json
  import tempfile
  import cPickle as pickle
  from xpedite.benchmark import makeBenchmark
  txnCount = 1000
  threadCount = 1
  tempDir = os.path.join(tempDir, appName) 

  cleanUpDataDir(tempDir, appName)

  _, dataFilePath, app, _, profiles = buildNotebook(tempDir, binary, txnCount, threadCount, workspace=workspace)
  replaceWorkspace(app.xpediteApp.appInfoPath, workspace, os.path.join(tempDir, 'xpedite-appinfo.txt'))
  copy(dataFilePath, os.path.join(tempDir, 'reportCmdBaseline.xpd'))
  
  fullCpuInfo = app.xpediteApp.env.proxy.fullCpuInfo
  baselineCpuInfoPath = os.path.join(tempDir, 'baselineCpuInfo.json')
  with open(baselineCpuInfoPath, 'w') as fileHandle:
    json.dump(fullCpuInfo, fileHandle)

  for dataFile in app.xpediteApp.gatherFiles(app.xpediteApp.sampleFilePattern()):
    copy(dataFile, os.path.join(tempDir, os.path.basename(dataFile)))
  
  makeBenchmark(profiles, os.path.join(tempDir, 'benchmark'))

  benchmarkAppInfo = os.path.join(tempDir, 'benchmark/benchmark/appinfo.txt')
  replaceWorkspace(benchmarkAppInfo, workspace, benchmarkAppInfo)

  benchmarkProfilePath = os.path.join(tempDir, 'profileInfoWithBenchmark.py')
  _, benchmarkDataFilePath, _, _, _ = buildNotebook(
    tempDir, binary, txnCount, threadCount, profileInfoPath=benchmarkProfilePath,
    runId=app.xpediteApp.runId, workspace=workspace
  )
  copy(benchmarkDataFilePath, os.path.join(tempDir, 'reportCmdBaselineWithBenchmark.xpd'))
  
  profileInfo = loadProfileInfo(tempDir, os.path.join(tempDir, 'profileInfo.py'))
  probes = loadProbes(binary, profileInfo, txnCount, threadCount, workspace=workspace)
  with open(os.path.join(tempDir, 'probeCmdBaseline.pkl'), 'wb') as probeFileHandle:
    probeFileHandle.write(pickle.dumps(probes))

def main():
  """
  Set the path to the data directory generated baseline files are stored in and
  generate files
  """
  import sys
  tempDir = sys.argv[1]
  appName = sys.argv[2]
  workspace = os.path.join(os.path.abspath(__file__).split('/test/')[0], '')
  testDir = os.path.abspath(os.path.dirname(__file__))
  dataDir = os.path.join(testDir, '..', 'data')
  binary = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..', 'install/test/slowFixDecoder'))
  generateBaseline(binary, tempDir, workspace, appName)

if __name__ == '__main__':
  main()
