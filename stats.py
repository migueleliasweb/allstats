import platform
from multiprocessing import cpu_count
import json
from os import statvfs
from math import pow
from docker import Client
from uptime import uptime
import utils


def host_stats():
    return {
        'uptime': int(uptime()),
        'linux': ''.join(platform.linux_distribution()),
        'kernel': platform.uname()[2],
        'cpu': {
            'cpu_count': cpu_count(),
            'model_name': cpu_model_name()
        },
        'memory': memory_stats(),
        'network': network_stats(),
        'disk': disk_stats(),
        'docker': docker_stats()
    }


def memory_stats():
    _meminfo=dict()

    with open('/proc/meminfo') as f:
        for line in f:
            _meminfo[line.split(':')[0]] = line.split(':')[1].strip().split(' ')[0]
    return {
        'memory_total': _meminfo['MemTotal'],
        'memory_free': _meminfo['MemFree'],
        'swap_total': _meminfo['SwapTotal'],
        'swap_free': _meminfo['SwapFree']
    }


def cpu_model_name():
    with open('/proc/cpuinfo') as f:
        for line in f:
            # Ignore the blank line separating the information between
            # details about two processing units
            if line.strip():
                if line.rstrip('\n').startswith('model name'):
                    model_name = line.rstrip('\n').split(':')[1]
                    return model_name


def network_stats():
    data = {}

    network_stats_file = '/tmp/network_stats'

    # last_stats = False
    # last_stats_time = False
    #
    # if path.isfile(network_stats_file):
    #     last_stats_time = datetime.fromtimestamp(path.getmtime(network_stats_file))
    #
    #     with open(network_stats_file, 'r') as _file:
    #         last_stats = json.loads(_file.read())

    with open('/proc/net/dev', 'r') as _file:
        next(_file)
        next(_file)

        for line in _file:
            line = list(filter(None, line.strip().split(' ')))

            _interface = line[0].replace(':', '')

            total_received_bytes = line[1]
            total_transmitted_bytes = line[9]

            #print(total_received_bytes+':'+last_stats[_interface]['receive']['total_bytes'])

            # avg_received_bytes = 0
            # avg_transmitted_bytes = 0
            #
            # if last_stats_time:
            #     seconds = (datetime.now() - last_stats_time).total_seconds()
            #     avg_received_bytes = int((int(total_received_bytes) - int(last_stats[_interface]['receive']['total_bytes'])) / seconds)
            #     avg_received_bytes = int(avg_received_bytes/1024)

            data[_interface] = {
                'receive': {
                    'total_bytes': total_received_bytes,
                    'total_packets': line[2],
                    'total_errors': line[3],
                    'avg': 0
                },
                'transmit': {
                    'total_bytes': total_transmitted_bytes,
                    'total_packets': line[10],
                    'total_errors': line[11],
                    'avg': 0
                }
            }

    with open(network_stats_file, 'w+') as dumpfile:
        dumpfile.write(json.dumps(data, sort_keys=True, indent=4))

    return data


def disk_stats():
    stats = statvfs('/')

    data = {
        '/': {
            'total': int((stats.f_bsize * stats.f_blocks) / pow(1024, 2)),
            'free': int((stats.f_bsize * stats.f_bfree) / pow(1024, 2))
        }
    }

    return data


def docker_stats():
    docker_client = Client(base_url='unix://var/run/docker.sock', version='1.20')

    data = {
        'version': docker_client.version(),
        'images': docker_client.images(),
        'containers': []
    }

    containers = docker_client.containers()

    for container in containers:
        _container_details = docker_client.inspect_container(container=container['Id'])
        _image_details = docker_client.inspect_image(image=_container_details['Image'])

        container['Image'] = _image_details

        last_log = docker_client.logs(
            container=container['Id'],
            stdout=True,
            stderr=True,
            tail=1,
            timestamps=True
        )

        container['last_log'] = str(last_log, 'UTF-8').strip().split(' ')[0]

        data['containers'].append(container)

    return utils.dict_keys_to_lower(data)


if __name__ == "__main__":
    print(json.dumps(host_stats(), sort_keys=True, indent=4))