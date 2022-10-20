# Installation
**Steps for client installation:**
1) ```pip install -r requirements.txt```
2) ```python setup.py install```

Clouni client is ready to use! 
Write ```clouni -h``` to get help.

**Steps for remote server installation:**

Fill the hosts.ini file like this:
```
[provider_tool_host]
1.1.1.1 ansible_user=ubuntu
[configuration_tool_host]
2.2.2.2 ansible_user=ubuntu
[grpc_cotea_host]
3.3.3.3 ansible_user=ubuntu
```
Then run:

```ansible-playbook main.yaml -i hosts.ini```

**Steps for local server installation:**

Replace addresses for 127.0.0.1 or localhost in hosts.ini

**Configure endpoints**

Write this to configure microservices endpoints (or use cli options):
```
export GRPC_COTEA_ENDPOINT=127.0.0.1:50151
export CLOUNI_PROVIDER_TOOL_ENDPOINT=127.0.0.1:50051
export CLOUNI_CONFIGURATION_TOOL_ENDPOINT=127.0.0.1:50052
export DATABASE_API_ENDPOINT=127.0.0.1:5000
```
