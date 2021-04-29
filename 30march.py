import subprocess
import yaml
import sys
import os
import time
import pprint

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

  else:
    print('    Failed to get cluster list')
    exit(1)


def scaleDown(clusters):
  for cluster in clusters:
    if cluster['NAME'].lower() == clusterName.lower() or clusterName == 'ALL':
      print('ClusterName = {0}'.format(cluster['NAME']))
      if cluster['NUM_NODES'] is not None and int(cluster['NUM_NODES']) != 0:
        if labelOrNodeCount in cluster['LABEL'] and (cluster['LABEL'][labelOrNodeCount] == 'true' or cluster['LABEL'][labelOrNodeCount] != 'false'):
          print('    Updating number of Nodes=0 in Cluster={0}'.format(cluster['NAME']))
          proc = subprocess.Popen(['gcloud', 'container', 'clusters', 'resize', cluster['NAME'], '--zone', cluster['ZONE'], '--num-nodes=0', '--verbosity', 'info'],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
          output, error = proc.communicate(input=b'\n')
          print('    Output =', output)
          print('    Error =', error)

          maxSleep = 600
          sleepTime = 120
          totalSleepTime = 0
          currentNodeCount = -1
          while currentNodeCount is not None:
            print('    Sleeping for {0} Seconds to get currentNodeCount.......'.format(sleepTime))
            time.sleep(sleepTime)
            p = subprocess.Popen(['gcloud', 'container', 'clusters', 'describe', cluster['NAME'], '--zone', cluster['ZONE']],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = p.communicate()
            currentNodeCount = yaml.safe_load(output).get('currentNodeCount')
            totalSleepTime += sleepTime
            if totalSleepTime >= maxSleep:
              break

          if currentNodeCount is None or (currentNodeCount is not None and int(currentNodeCount) == 0):
            print('    Number of Nodes=0 updated successfully in Cluster={0}'.format(cluster['NAME']))
          else:
            print('    Failed to update Number of Nodes=0 in Cluster={0}'.format(cluster['NAME']))
        else:
          print('    {0} label is not set for Cluster={1}'.format(labelOrNodeCount, cluster['NAME']))
      else:
        print('    Cluster={0} already has Number of Nodes=0'.format(cluster['NAME']))

    if cluster['NAME'].lower() == clusterName.lower():
      break


def scaleUp(clusters):
  for cluster in clusters:
    if cluster['NAME'].lower() == clusterName.lower():
      print('ClusterName = {0}'.format(cluster['NAME']))
      if cluster['NUM_NODES'] is None or (cluster['NUM_NODES'] is not None and int(cluster['NUM_NODES']) != int(labelOrNodeCount)):
        print('    Updating number of Nodes={0} in Cluster={1}'.format(labelOrNodeCount, clusterName))
        numNodes = '--num-nodes={0}'.format(labelOrNodeCount)
        proc = subprocess.Popen(['gcloud', 'container', 'clusters', 'resize', cluster['NAME'], '--zone', cluster['ZONE'], numNodes, '--verbosity', 'info'],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = proc.communicate(input=b'\n')
        print('    Output =', output)
        print('    Error =', error)

        maxSleep = 600
        sleepTime = 120
        totalSleepTime = 0
        currentNodeCount = 0
        while int(currentNodeCount) != int(labelOrNodeCount):
          print('    Sleeping for {0} Seconds to get currentNodeCount.......'.format(sleepTime))
          time.sleep(sleepTime)
          p = subprocess.Popen(['gcloud', 'container', 'clusters', 'describe', cluster['NAME'], '--zone', cluster['ZONE']],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
          output, error = p.communicate()
          currentNodeCount = yaml.safe_load(output).get('currentNodeCount')
          totalSleepTime += sleepTime
          if totalSleepTime >= maxSleep:
            break

        if int(currentNodeCount) == int(labelOrNodeCount):
          print('    Number of Nodes={0} updated successfully in Cluster={1}'.format(labelOrNodeCount, clusterName))
        else:
          print('    Failed to update Number of Nodes={0} in Cluster={1}'.format(labelOrNodeCount, clusterName))
      else:
        print('    Cluster={0} already has Number of Nodes={1}'.format(cluster['NAME'], labelOrNodeCount))


if __name__ == '__main__':
  if len(sys.argv) - 1 != 4:
    print('Please pass required arguments to the script')
    print('Usage: python shutdownCluster.py <Project ID> <Cluster Name/ALL(Scaledown all clusters)> <UP/DOWN> <Label(For ScaleDown)/NodeCount(For ScaleUp)>')
    exit(1)
  projectId = sys.argv[1]
  clusterName = sys.argv[2]
  operationType = sys.argv[3]
  labelOrNodeCount = sys.argv[4]
  print('Project ID = {0}, Cluster Name = {1}'.format(projectId, clusterName))
  #
  #os.system("gcloud auth login")
  #os.system("gcloud auth activate-service-account jenkins-test@inspiring-keel-308108.iam.gserviceaccount.com --key-file=jenkins-test.json")
  #os.system("gcloud config set account trygcponce@gmail.com")
  cmd = "gcloud config set project {0}".format(projectId)
  os.system(cmd)
  clusters = getClusterList()
  #pprint.pprint(clusters)
  if operationType == 'UP':
    scaleUp(clusters)
  elif operationType == 'DOWN':
    scaleDown(clusters)
