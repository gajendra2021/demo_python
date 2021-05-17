import yaml
import sys
import time
import os
import pprint
import subprocess
from datetime import datetime
from subprocess import Popen, PIPE


def getClusterList():
  print('Getting Cluster list for the Project={0}'.format(projectId))
  clusters = []
  p = subprocess.Popen(['gcloud', 'container', 'clusters', 'list', '--project', projectId, '--format="json"'],
                       stdout=subprocess.PIPE, stderr = subprocess.PIPE)
  output, error = p.communicate()
  if output:
    output = yaml.safe_load(output)
    for data in output:
      cluster = {}
      cluster['NAME'] = data.get('name')
      cluster['ZONE'] = data.get('zone')
      cluster['STATUS'] = data.get('status')
      cluster['LOCATION'] = data.get('location')
      cluster['LABEL'] = data.get('resourceLabels')
      cluster['NUM_NODES'] = data.get('currentNodeCount')
      clusters.append(cluster)
    pprint.pprint(clusters)
    return clusters

def setClusterContext(projectId, clusterName, clusters):
  for cluster in clusters:
    if cluster['NAME'].lower() == clusterName.lower():
      clusterZone = cluster['ZONE']
      break
      
  currentContext = Popen(['kubectl', 'config', 'current-context'],
                         stdout=PIPE, stderr=PIPE).communicate()[0]
  
  clusterContext = 'gke_' + projectId + '_' + clusterZone + '_' + clusterName
  if clusterContext.encode() not in currentContext:
    print('Cluster Context= {0}'.format(clusterContext))
    Popen(['gcloud', 'container', 'clusters', 'get-credentials', clusterName,
           '--zone', clusterZone, '--project', projectId], stdout=PIPE, stderr=PIPE).communicate()
      
def getNamespaces():
  print('Getting namespaces list for the Project={0}'.format(projectId))
  namespaces = []
  p = Popen(['kubectl','get','pods','--all-namespaces'], stdout=PIPE,
  stderr = PIPE)
  output, error = p.communicate()
  print("stdout=",output)
  print("stdout=",error)
  if not error:
    #above command returns bytes type output so using decode to convert
    allData = output.decode("utf-8").rstrip().split('\n')
    print(allData)
    fields = allData[0].split()
    for i in range(1, len(allData)):
      namespace = {}
      row = allData[i].split()
      for j in range(len(fields)):
        namespace[fields[j]] = row[j]
      namespaces.append(namespace)
    return namespaces
    

  else:
    print('Failed to get namespaces list')
    exit(1)

def helm_del(namespace):
  p1 = Popen(['helm', 'ls','-a','--all-namespaces'], stdout=PIPE, stderr=PIPE)
  p2 = Popen(['awk','NR>1 {print $1,$4}'],stdin=p1.stdout,stdout=PIPE)
#p  = Popen(['awk','NR>1 {print $1}'],stdout=PIPE,stderr=PIPE)
  stdout, stderr = p2.communicate()
  
  td_date=datetime.now()
  td_date=td_date.strftime("%Y-%m-%d")

  if not stderr:
    allData= stdout.decode("utf-8").rstrip().split('\n')
    for string in allData:
      name=string.split()[0]
      dep_date=string.split()[1]
      tdelta = datetime.strptime(td_date, '%Y-%m-%d') - datetime.strptime(dep_date, '%Y-%m-%d')
      #print(name,tdelta.days)
      if tdelta.days == 0:
        print(name)
      
        p3=Popen(['helm','delete',name],stdout=PIPE,stderr=PIPE).communicate()
        #stdout.stderr=p3.communicate()
      
        #p3=Popen(['xargs','helm','delete'],stdin=p.stdout,stdout=PIPE)
        #stdout,stderr=p3.communicate()
      
  
if __name__ == '__main__':
  if len(sys.argv) - 1 != 2:
    print('Please pass required arguments to the script')
    print('Usage: python shutdownCluster.py <Project ID> <Cluster Name>')
    exit(1)
  projectId = sys.argv[1]
  clusterName = sys.argv[2]
  print('Project ID = {0}, Cluster Name = {1}'.format(projectId, clusterName))
  #os.system("gcloud auth activate-service-account jenkins-test@inspiring-keel-308108.iam.gserviceaccount.com --key-file=jenkins-test.json")
  os.system("gcloud container clusters get-credentials cluster-2 --zone us-east1-b --project inspiring-keel-308108")
  #os.system("gcloud components install kubectl")
  os.system("kubectl config use-context gke_inspiring-keel-308108_us-east1-b_cluster-2")
  #os.system("gcloud config set account trygcponce@gmail.com")
  cmd = "gcloud config set project {0}".format(projectId)
  os.system(cmd)
  clusters = getClusterList()
  setClusterContext(projectId, clusterName, clusters)
  namespaces = getNamespaces()
  helm_del(namespaces)
