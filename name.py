import sys
import re
import yaml, json
from subprocess import Popen, PIPE, call, CalledProcessError


def _escape_ansi(line):
    ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', line)


class GcloudContainClusters:

    def __init__(self, project, cluster):
        self.projectId = project.lower()
        self.clustername = cluster.lower()
        self.containerlist = Popen(['gcloud',
                                    'container',
                                    'clusters',
                                    'list',
                                    '--project',
                                    self.projectId,
                                    '--format="json"'],
                                   stdout=PIPE, stderr=PIPE).communicate()[0]
        self.currentcontext = Popen(['kubectl',
                                     'config',
                                     'current-context'],
                                    stdout=PIPE, stderr=PIPE).communicate()[0]

        self.output = yaml.safe_load(self.containerlist)

    def get_cluster_details(self):
        clusters = []

        for data in self.output:
            if self.clustername == data.get('name').lower():
                cluster = {}
                cluster['NAME'] = data.get('name')
                cluster['ZONE'] = data.get('zone')
                cluster['STATUS'] = data.get('status')
                cluster['LOCATION'] = data.get('location')
                cluster['LABEL'] = data.get('resourceLabels')
                cluster['NUM_NODES'] = data.get('currentNodeCount')
                clusters.append(cluster)

        if not clusters:
            print("ClusterName=" + self.clustername + " doesn't exist in the Project=" + self.projectId)
            exit(1)

        return clusters

    def switch_cluster_context(self, cluster_zone):
        """
    Script is designed to remote jenkins invoke or has to be copied over to targeted
    gke cluster. switching cluster method is to switch given cluster name as input once
    current context is not matched with given cluster context.
    :param cluster_zone: is input to filter correct cluster name.
    """

        clustercontext = 'gke_' + self.projectId + '_' + cluster_zone + '_' + self.clustername

        if clustercontext.encode() not in self.currentcontext:
            print('Cluster = {0}'.format(clustercontext))
            Popen(['gcloud',
                   'container',
                   'clusters',
                   'get-credentials',
                   self.clustername,
                   '--zone', cluster_zone,
                   '--project', self.projectId],
                  stdout=PIPE, stderr=PIPE).communicate()

    def get_cluster_namespaces(self, creationtime='30 days ago'):
        """
    30 days old namespaces are filtered by creationtime.
    :param creationtime: namespaces creation time can be overwritten by custom input.
    :return: namespacelist is decoded string not a python list.
    """

        try:
            command = r"""
                  kubectl get namespaces -o go-template --template '{{range .items}}{{.metadata.name}} {{.metadata.creationTimestamp}}{{"\n"}}{{end}}' | 
                  awk '$2 <= "'$(date -d '%s' -Ins --utc | 
                  sed 's/+0000/Z/')'" && $1 !~ /(default|cert-manager|kube.*|kube-*)/ { print $1 }' | 
                  xargs --no-run-if-empty
                  """ % (creationtime)

            namespaceslist = Popen(command, shell=True,
                                   stdout=PIPE, stderr=PIPE).communicate()[0].strip().decode('utf-8')

            return namespaceslist
            namespaceslist.close()
            namespaceslist.wait()

        except CalledProcessError as e:
            if e.output.startswith('error: {'):
                error = json.loads(e.output[7:])
                print(error['code'])
                print(error['message'])

    def get_namespace_pods(self, namespace, creationtime='now-0 hours'):
        """
    pods created by old ReplicaSet are terminated, new ReplicaSet created brand new pod
    with restarts 0 and age 0 sec can be filtered by datetime (optional).
    :param namespace: is input to filter podlist.
    :param creationtime: can be overwritten by input datetime.
    :return: podslist is decoded string not a python list.
    """

        try:
            command = r"""
                  kubectl get pods -n '%s' -o go-template --template '{{range .items}}{{.metadata.name}} {{.metadata.creationTimestamp}}{{"\n"}}{{end}}' | 
                  awk '$2 <= "'$(date -d '%s' -Ins --utc | 
                  sed 's/+0000/Z/')'" { print $1 }' | 
                  xargs --no-run-if-empty
                  """ % (namespace, creationtime)

            podslist = Popen(command, shell=True,
                             stdout=PIPE, stderr=PIPE).communicate()[0].strip().decode('utf-8')

            return podslist
            podslist.close()
            podslist.wait()

        except CalledProcessError as e:
            if e.output.startswith('error: {'):
                error = json.loads(e.output[7:])
                print(error['code'])
                print(error['message'])

    def del_pods(self, namespace, pods):
        """
    Pods are often stuck in terminating state after helm uninstall.
    del_pods will delete pods.
    :param namespace: is input.
    :param pods: pods is/are input.
    :return: deletion status=0 pass, if status=1 delete empty namespace.
    """

        try:
            if pods:
                status = call(['kubectl',
                               'delete',
                               'pod',
                               '--grace-period=0',
                               '--force'
                               '--namespace'] +
                              str(namespace).split(" ") +
                              str(pods).split(" "))
            else:
                status = 1

            return status

        except CalledProcessError as e:
            if e.output.startswith('error: {'):
                error = json.loads(e.output[7:])
                print(error['code'])
                print(error['message'])

    def del_namespaces(self, namespaces):
        """
    Delete Namespace that is 30 days old.
    :param namespaces: is input.
    """

        try:
            status = call(['kubectl',
                           'delete',
                           'namespace'] +
                          str(namespaces).split(" ")
                          )
            return status

        except CalledProcessError as e:
            if e.output.startswith('error: {'):
                error = json.loads(e.output[7:])
                print(error['code'])
                print(error['message'])


def main():
    GKEcontainer = GcloudContainClusters(project=sys.argv[1], cluster=sys.argv[2])
    clusters = GKEcontainer.get_cluster_details()
    for cluster in clusters:
        GKEcontainer.switch_cluster_context(cluster_zone=cluster['ZONE'])
        namespaces = GKEcontainer.get_cluster_namespaces(creationtime='30 days ago')

        for namespace in list(str(namespaces).split(" ")):
            pods = GKEcontainer.get_namespace_pods(namespace=namespace)
            if pods:
                status = GKEcontainer.del_pods(namespace=namespace, pods=pods)
                if status != 0:
                    print("Failed to delete " + ('namespace = {0}', 'pods = {1}'.format(namespace, pods)))

        # delete all empty namespaces < 30 days old
        status = GKEcontainer.del_namespaces(namespaces=namespaces)
        if status != 0:
            print("Failed to delete " + ('namespaces = {0}'.format(namespaces)))


if __name__ == "__main__":
    main()
