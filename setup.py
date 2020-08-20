#!/usr/bin/python
# Internal Libraries
import os
import sys
import yaml
import json
import argparse
from multiprocessing import Pool, TimeoutError
from subprocess import DEVNULL, STDOUT, check_call

# External Libraries
from questions.k8s import k8sQuestion, buildKubePrimaryFile
from questions.inventory import inventoryQuestions
from functions.files import createK8sOutputFile, createBoltFile
from functions.eval import evalSocketUptime, activeInventory

# Sets up args
parser = argparse.ArgumentParser(description="Sets up your homelab environment with Bolt")
parser.add_argument('--boltdir', '-b',
    help="Defines your Boltdir. Defaults to 'Boltdir'.",
    default='Boltdir')
parser.add_argument('--debug',
    help="Enabled debug log output.",
    action="store_true", default=False)

# Parses all of your args.
args = parser.parse_args()

# Definitions
directory = "{}/data".format(args.boltdir)
puppetDir = os.getcwd() + '/' + args.boltdir
inventoryFileName = "{}/inventory.yaml".format(args.boltdir)

# Create the directory to do everything in.
try:
    os.makedirs(directory + '/', exist_ok = True)
except:
    raise

# Questionnaire time!
print("We're going to ask you a few questions to get your environment up and going.")

# Functions
## K8s Questions
ktDir, ktEnvFile, ktOS, ktCNI_PROVIDER, etcdClusterHostname, kubePrimary = k8sQuestion(directory=directory)

## Inventory Questions
inventoryFile = inventoryQuestions(kubePrimary)

## Run Docker Builder
check_call([
    "/usr/bin/docker", "run", "--rm", "-v", "{}:/mnt".format(ktDir), 
    "--env-file", ktEnvFile, "puppet/kubetool:5.1.0"],
    stdout=DEVNULL, stderr=STDOUT)

# Generate the list of Values, list of Certs, and the filename 
listOfThings, listOfCerts, k8sFile = buildKubePrimaryFile(ktDir, ktOS, ktCNI_PROVIDER, etcdClusterHostname)

# Create the k8s Output File
createK8sOutputFile(listOfThings, listOfCerts, k8sFile, inventoryFileName, inventoryFile)

# Create Bolt Files
createBoltFile('bolt-project.yaml', '{}/Bolt.yaml'.format(puppetDir))
createBoltFile('hiera.yaml', '{}/hiera.yaml'.format(puppetDir))
createBoltFile('Puppetfile', '{}/Puppetfile'.format(puppetDir))
createBoltFile('common.yaml', '{}/data/common.yaml'.format(puppetDir))
createBoltFile('site-modules/deploy_k8s/plans/deploy.pp', '{}/site-modules/deploy_k8s/plans/deploy.pp'.format(puppetDir))
createBoltFile('site-modules/deploy_k8s/plans/nuke.pp', '{}/site-modules/deploy_k8s/plans/nuke.pp'.format(puppetDir))

# Remove the env file.
# os.remove("{}/data/env".format(args.boltdir))

# Get a list of all of the hosts in active inventory:
listOfHosts = activeInventory(args.boltdir)

# Evaluate if the hosts actually have their SSH sockets open
print("Evaluating if all hosts are alive:")
if __name__ == '__main__':
    with Pool(os.cpu_count()) as p:
        p.map(evalSocketUptime, listOfHosts)
