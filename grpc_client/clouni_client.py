from distutils.dir_util import copy_tree

import paramiko
from scp import SCPClient

import six
import yaml

from grpc_client.api_pb2 import ClouniProviderToolResponse, ClouniProviderToolRequest, ClouniConfigurationToolRequest
import grpc_client.api_pb2_grpc as api_pb2_grpc
import grpc
import sys
import os
import argparse


def createSSHClient(server, user):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, username=user)
    return client


def get_project_root_path():
    return os.path.dirname(os.path.dirname(__file__))

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    default_provider_tool_endpoint = os.environ.get("CLOUNI_PROVIDER_TOOL_ENDPOINT")
    default_configuration_tool_endpoint = os.environ.get("CLOUNI_CONFIGURATION_TOOL_ENDPOINT")
    default_grpc_cotea_endpoint = os.environ.get("GRPC_COTEA_ENDPOINT")
    default_database_api_endpoint = os.environ.get("DATABASE_API_ENDPOINT")
    if default_provider_tool_endpoint is None:
        default_provider_tool_endpoint = '127.0.0.1:50051'
    if default_configuration_tool_endpoint is None:
        default_configuration_tool_endpoint = '127.0.0.1:50052'
    parser = argparse.ArgumentParser(prog="clouni", formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('module',
                        choices=['provider_tool', 'configuration_tool', 'deploy', 'delete'],
                        metavar='<MODULE>',
                        help='use provider_tool for creating provider template and writing it to stdout or file \n'
                             'use configuration_tool for translating and deploying ansible generated from provider '
                             'template (or getting ansible playbook with --debug) \n'
                             'use deploy/delete for deploying/deleting TOSCA normative template '
                             '(or getting ansible playbook with --debug) \n'
                        )
    parser.add_argument('--template-file',
                        metavar='<filename>',
                        required=True,
                        help='YAML template to parse')
    parser.add_argument('--cluster-name',
                        required=True,
                        metavar='<unique_name>',
                        help='cluster name')
    parser.add_argument('--validate-only',
                        action='store_true',
                        default=False,
                        help='only validate input template, do not perform translation')
    parser.add_argument('--delete',
                        action='store_true',
                        default=False,
                        help='delete cluster')
    parser.add_argument('--provider',
                        choices=['openstack', 'amazon', 'kubernetes'],
                        required=False,
                        help='cloud provider name to execute ansible playbook in')
    parser.add_argument('--output-file',
                        metavar='<filename>',
                        required=False,
                        help='output file')
    parser.add_argument('--configuration-tool',
                        default="ansible",
                        choices=['ansible', 'kubernetes'],
                        help="configuration tool which DSL the template would be translated to"
                             "Default value = \"ansible\"")
    parser.add_argument('--extra',
                        default=[],
                        metavar="KEY=VALUE",
                        nargs='+',
                        help='extra arguments for configuration tool scripts')
    parser.add_argument('--debug',
                        default=False,
                        action='store_true',
                        help='set debug level for tool')
    parser.add_argument('--log-level',
                        default='info',
                        choices=['debug', 'info', 'warning', 'error', 'critical'],
                        help='set log level for tool')
    parser.add_argument('--host-parameter',
                        metavar='<parameter>',
                        default='public_address',
                        help="specify Compute property to be used as host IP for software components that hosted "
                             "on the Compute\nvalid values: public_address and private_address")
    parser.add_argument('--public-key-path',
                        default='~/.ssh/id_rsa.pub',
                        metavar='<path>',
                        help="set path to public key for configuration software on cloud servers")
    parser.add_argument('--provider-tool-endpoint',
                        type=str,
                        metavar='<host:port>',
                        default=default_provider_tool_endpoint,
                        help='endpoint of provider tool server, default - localhost:50051')
    parser.add_argument('--configuration-tool-endpoint',
                        metavar='<host:port>',
                        default=default_configuration_tool_endpoint,
                        type=str,
                        help='endpoint of configuration tool server, default - localhost:50052')
    parser.add_argument('--database-api-endpoint',
                        default=default_database_api_endpoint,
                        metavar='<host:port>',
                        type=str,
                        help='endpoint of database api for tosca template storage, default - localhost:5000')
    parser.add_argument('--grpc-cotea-endpoint',
                        default=default_grpc_cotea_endpoint,
                        metavar='<host:port>',
                        type=str,
                        help='endpoint of grpc-cotea, default - localhost:50151')

    (args, args_list) = parser.parse_known_args(args)

    provider_tool_user = os.environ.get("GRPC_COTEA_HOST_USER")
    extra = {}
    for i in args.extra:
        i_splitted = [j.strip() for j in i.split('=', 1)]
        if len(i_splitted) < 2:
            raise Exception('Failed parsing parameter \'--extra\', required \'key=value\' format')
        extra.update({i_splitted[0]: i_splitted[1]})

    for k, v in extra.items():
        if isinstance(v, six.string_types):
            if v.isnumeric():
                if int(v) == float(v):
                    extra[k] = int(v)
                else:
                    extra[k] = float(v)
    if default_grpc_cotea_endpoint:
        if default_grpc_cotea_endpoint.find('127.0.0.1') == -1 and default_grpc_cotea_endpoint.find(
                'localhost') == -1:
            if not provider_tool_user:
                print("Warning! GRPC_COTEA_HOST_USER not set. "
                      "You may have problems with access to your custom artifacts for TOSCA operations and ansible modules!")
            else:
                server, port = default_grpc_cotea_endpoint.split(":")
                ssh = createSSHClient(server, provider_tool_user)
                client = SCPClient(ssh.get_transport())
                if not client:
                    raise Exception(
                        'Failed to connect % via ssh for adding custom artifacts' % default_grpc_cotea_endpoint)
                client.put(os.path.join(get_project_root_path(), 'ansible_plugins'), '/tmp/clouni/', recursive=True)
                client.put(os.path.join(get_project_root_path(), 'artifacts'), '/tmp/clouni/', recursive=True)

        else:
            copy_tree(os.path.join(get_project_root_path(), 'ansible_plugins'), '/tmp/clouni/ansible_plugins')
            copy_tree(os.path.join(get_project_root_path(), 'artifacts'), '/tmp/clouni/artifacts')
    if args.module in ['provider_tool', 'deploy', 'delete']:
        channel = grpc.insecure_channel(args.provider_tool_endpoint)
        stub = api_pb2_grpc.ClouniProviderToolStub(channel)
        request = ClouniProviderToolRequest()
        if args.module == 'provider_tool':
            args.configuration_tool_endpoint = ""
        if args.module == 'delete':
            args.delete = True
        template_file = os.path.join(os.getcwd(), args.template_file)
        with open(template_file, 'r') as f:
            template_content = f.read()
        request.template_file_content = template_content
        request.cluster_name = args.cluster_name
        request.validate_only = args.validate_only
        request.delete = args.delete
        if args.provider is not None:
            request.provider = args.provider
        else:
            if args.validate_only:
                request.provider = ""
            else:
                raise Exception("Can't generate ansible without --provider argument")
        request.configuration_tool = args.configuration_tool
        request.log_level = args.log_level
        request.debug = args.debug
        request.host_parameter = args.host_parameter
        request.public_key_path = args.public_key_path
        if args.configuration_tool_endpoint is not None:
            request.configuration_tool_endpoint = args.configuration_tool_endpoint
        else:
            request.configuration_tool_endpoint = ""

        if args.database_api_endpoint is not None:
            request.database_api_endpoint = args.database_api_endpoint
        else:
            request.database_api_endpoint = ""
        if args.grpc_cotea_endpoint is not None:
            request.grpc_cotea_endpoint = args.grpc_cotea_endpoint
        else:
            request.grpc_cotea_endpoint = ""

        request.extra = yaml.dump(extra)
        response = stub.ClouniProviderTool(request)
    elif args.module in ['configuration_tool']:
        channel = grpc.insecure_channel(args.configuration_tool_endpoint)
        stub = api_pb2_grpc.ClouniConfigurationToolStub(channel)
        request = ClouniConfigurationToolRequest()
        template_file = os.path.join(os.getcwd(), args.template_file)
        with open(template_file, 'r') as f:
            template_content = f.read()

        request.provider_template = template_content
        request.cluster_name = args.cluster_name
        request.delete = args.delete
        request.configuration_tool = args.configuration_tool
        request.log_level = args.log_level
        request.debug = args.debug
        request.validate_only = args.validate_only

        if args.database_api_endpoint is not None:
            request.database_api_endpoint = args.database_api_endpoint
        else:
            request.database_api_endpoint = ""

        if args.grpc_cotea_endpoint is not None:
            request.grpc_cotea_endpoint = args.grpc_cotea_endpoint
        else:
            request.grpc_cotea_endpoint = ""

        request.extra = yaml.dump({'global': extra})
        response = stub.ClouniConfigurationTool(request)
    else:
        raise Exception("Unknown module type")

    if not response:
        raise Exception("Server don't response")
    print("* Status *\n")
    status = ['TEMPLATE_VALID', 'TEMPLATE_INVALID', 'OK', 'ERROR']
    print(status[response.status])
    if response.error:
        print("\n* Error *\n")
        print(response.error)
    if response.content:
        if args.debug:
            print("\n* Content *\n")
            print(response.content)
        if args.output_file:
            with open(args.output_file, 'w') as file_obj:
                file_obj.write(response.content)