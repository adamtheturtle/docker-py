from .. import errors
from ..utils.utils import (
    convert_port_bindings, convert_tmpfs_mounts, convert_volume_binds,
    format_environment, format_extra_hosts, normalize_links, parse_bytes,
    parse_devices, split_command, version_gte, version_lt,
)
from .base import DictType
from .healthcheck import Healthcheck
from docker.errors import InvalidVersion
from docker.types.networks import NetworkingConfig
from typing import Dict, List, Optional, Tuple, Union


class LogConfigTypesEnum:
    _values = (
        'json-file',
        'syslog',
        'journald',
        'gelf',
        'fluentd',
        'none'
    )
    JSON, SYSLOG, JOURNALD, GELF, FLUENTD, NONE = _values


class LogConfig(DictType):
    """
    Configure logging for a container, when provided as an argument to
    :py:meth:`~docker.api.container.ContainerApiMixin.create_host_config`.
    You may refer to the
    `official logging driver documentation <https://docs.docker.com/config/containers/logging/configure/>`_
    for more information.

    Args:
        type (str): Indicate which log driver to use. A set of valid drivers
            is provided as part of the :py:attr:`LogConfig.types`
            enum. Other values may be accepted depending on the engine version
            and available logging plugins.
        config (dict): A driver-dependent configuration dictionary. Please
            refer to the driver's documentation for a list of valid config
            keys.

    Example:

        >>> from docker.types import LogConfig
        >>> lc = LogConfig(type=LogConfig.types.JSON, config={
        ...   'max-size': '1g',
        ...   'labels': 'production_status,geo'
        ... })
        >>> hc = client.create_host_config(log_config=lc)
        >>> container = client.create_container('busybox', 'true',
        ...    host_config=hc)
        >>> client.inspect_container(container)['HostConfig']['LogConfig']
        {
            'Type': 'json-file',
            'Config': {'labels': 'production_status,geo', 'max-size': '1g'}
        }
    """
    types = LogConfigTypesEnum

    def __init__(self, **kwargs) -> None:
        log_driver_type = kwargs.get('type', kwargs.get('Type'))
        config = kwargs.get('config', kwargs.get('Config')) or {}

        if config and not isinstance(config, dict):
            raise ValueError("LogConfig.config must be a dictionary")

        super().__init__({
            'Type': log_driver_type,
            'Config': config
        })

    @property
    def type(self):
        return self['Type']

    @type.setter
    def type(self, value) -> None:
        self['Type'] = value

    @property
    def config(self):
        return self['Config']

    def set_config_value(self, key, value) -> None:
        """ Set a the value for ``key`` to ``value`` inside the ``config``
            dict.
        """
        self.config[key] = value

    def unset_config(self, key) -> None:
        """ Remove the ``key`` property from the ``config`` dict. """
        if key in self.config:
            del self.config[key]


class Ulimit(DictType):
    """
    Create a ulimit declaration to be used with
    :py:meth:`~docker.api.container.ContainerApiMixin.create_host_config`.

    Args:

        name (str): Which ulimit will this apply to. The valid names can be
            found in '/etc/security/limits.conf' on a gnu/linux system.
        soft (int): The soft limit for this ulimit. Optional.
        hard (int): The hard limit for this ulimit. Optional.

    Example:

        >>> nproc_limit = docker.types.Ulimit(name='nproc', soft=1024)
        >>> hc = client.create_host_config(ulimits=[nproc_limit])
        >>> container = client.create_container(
                'busybox', 'true', host_config=hc
            )
        >>> client.inspect_container(container)['HostConfig']['Ulimits']
        [{'Name': 'nproc', 'Hard': 0, 'Soft': 1024}]

    """
    def __init__(self, **kwargs) -> None:
        name = kwargs.get('name', kwargs.get('Name'))
        soft = kwargs.get('soft', kwargs.get('Soft'))
        hard = kwargs.get('hard', kwargs.get('Hard'))
        if not isinstance(name, str):
            raise ValueError("Ulimit.name must be a string")
        if soft and not isinstance(soft, int):
            raise ValueError("Ulimit.soft must be an integer")
        if hard and not isinstance(hard, int):
            raise ValueError("Ulimit.hard must be an integer")
        super().__init__({
            'Name': name,
            'Soft': soft,
            'Hard': hard
        })

    @property
    def name(self):
        return self['Name']

    @name.setter
    def name(self, value) -> None:
        self['Name'] = value

    @property
    def soft(self):
        return self.get('Soft')

    @soft.setter
    def soft(self, value) -> None:
        self['Soft'] = value

    @property
    def hard(self):
        return self.get('Hard')

    @hard.setter
    def hard(self, value) -> None:
        self['Hard'] = value


class DeviceRequest(DictType):
    """
    Create a device request to be used with
    :py:meth:`~docker.api.container.ContainerApiMixin.create_host_config`.

    Args:

        driver (str): Which driver to use for this device. Optional.
        count (int): Number or devices to request. Optional.
            Set to -1 to request all available devices.
        device_ids (list): List of strings for device IDs. Optional.
            Set either ``count`` or ``device_ids``.
        capabilities (list): List of lists of strings to request
            capabilities. Optional. The global list acts like an OR,
            and the sub-lists are AND. The driver will try to satisfy
            one of the sub-lists.
            Available capabilities for the ``nvidia`` driver can be found
            `here <https://github.com/NVIDIA/nvidia-container-runtime>`_.
        options (dict): Driver-specific options. Optional.
    """

    def __init__(self, **kwargs) -> None:
        driver = kwargs.get('driver', kwargs.get('Driver'))
        count = kwargs.get('count', kwargs.get('Count'))
        device_ids = kwargs.get('device_ids', kwargs.get('DeviceIDs'))
        capabilities = kwargs.get('capabilities', kwargs.get('Capabilities'))
        options = kwargs.get('options', kwargs.get('Options'))

        if driver is None:
            driver = ''
        elif not isinstance(driver, str):
            raise ValueError('DeviceRequest.driver must be a string')
        if count is None:
            count = 0
        elif not isinstance(count, int):
            raise ValueError('DeviceRequest.count must be an integer')
        if device_ids is None:
            device_ids = []
        elif not isinstance(device_ids, list):
            raise ValueError('DeviceRequest.device_ids must be a list')
        if capabilities is None:
            capabilities = []
        elif not isinstance(capabilities, list):
            raise ValueError('DeviceRequest.capabilities must be a list')
        if options is None:
            options = {}
        elif not isinstance(options, dict):
            raise ValueError('DeviceRequest.options must be a dict')

        super().__init__({
            'Driver': driver,
            'Count': count,
            'DeviceIDs': device_ids,
            'Capabilities': capabilities,
            'Options': options
        })

    @property
    def driver(self):
        return self['Driver']

    @driver.setter
    def driver(self, value) -> None:
        self['Driver'] = value

    @property
    def count(self):
        return self['Count']

    @count.setter
    def count(self, value) -> None:
        self['Count'] = value

    @property
    def device_ids(self):
        return self['DeviceIDs']

    @device_ids.setter
    def device_ids(self, value) -> None:
        self['DeviceIDs'] = value

    @property
    def capabilities(self):
        return self['Capabilities']

    @capabilities.setter
    def capabilities(self, value) -> None:
        self['Capabilities'] = value

    @property
    def options(self):
        return self['Options']

    @options.setter
    def options(self, value) -> None:
        self['Options'] = value


class HostConfig(dict):
    def __init__(self, version: str, binds: Optional[Union[Dict[str, Dict[str, str]], Dict[str, Dict[str, Union[str, bool]]], List[str]]]=None, port_bindings: Optional[Union[Dict[int, Optional[int]], Dict[Union[int, str], Optional[Union[int, Tuple[int], Tuple[str], Tuple[str, int], List[Tuple[str]]]]]]]=None,
                 lxc_conf: Optional[Union[Dict[str, str], List[Dict[str, str]]]]=None, publish_all_ports: bool=False, links: Optional[Union[List[Tuple[str, str]], Dict[str, str]]]=None,
                 privileged: bool=False, dns: Optional[List[str]]=None, dns_search: Optional[List[str]]=None,
                 volumes_from: Optional[List[str]]=None, network_mode: Optional[str]=None, restart_policy: Optional[Union[Dict[str, str], Dict[str, Union[str, int]]]]=None,
                 cap_add: Optional[List[str]]=None, cap_drop: Optional[List[str]]=None, devices: Optional[List[str]]=None, extra_hosts: Optional[Dict[str, str]]=None,
                 read_only: Optional[bool]=None, pid_mode: Optional[str]=None, ipc_mode: Optional[str]=None,
                 security_opt: Optional[Union[str, List[str]]]=None, ulimits: Optional[Union[List[Dict[str, Union[str, int]]], List[Ulimit]]]=None, log_config: Optional[Union[Dict[str, str], Dict[str, Union[str, Dict[str, str]]], LogConfig]]=None,
                 mem_limit: Optional[Union[int, str, float]]=None, memswap_limit: Optional[int]=None, mem_reservation: Optional[int]=None,
                 kernel_memory: Optional[int]=None, mem_swappiness: Optional[Union[int, str]]=None, cgroup_parent: Optional[str]=None,
                 group_add: Optional[List[str]]=None, cpu_quota: Optional[Union[int, str, float]]=None, cpu_period: Optional[Union[int, str, float]]=None,
                 blkio_weight: Optional[int]=None, blkio_weight_device: Optional[List[Dict[str, Union[str, int]]]]=None,
                 device_read_bps: Optional[List[Dict[str, Union[str, int]]]]=None, device_write_bps: Optional[List[Dict[str, Union[str, int]]]]=None,
                 device_read_iops: Optional[List[Dict[str, Union[str, int]]]]=None, device_write_iops: Optional[List[Dict[str, Union[str, int]]]]=None,
                 oom_kill_disable: bool=False, shm_size: Optional[Union[int, str]]=None, sysctls: Optional[Union[Dict[str, str], Dict[str, Union[str, int]]]]=None,
                 tmpfs: Optional[Union[Dict[str, str], List[str]]]=None, oom_score_adj: Optional[Union[int, str]]=None, dns_opt: Optional[List[str]]=None, cpu_shares: Optional[int]=None,
                 cpuset_cpus: Optional[str]=None, userns_mode: Optional[str]=None, uts_mode: Optional[str]=None,
                 pids_limit: Optional[Union[int, str]]=None, isolation: Optional[Union[Dict[str, str], str]]=None, auto_remove: bool=False,
                 storage_opt: None=None, init: None=None, init_path: None=None,
                 volume_driver: Optional[str]=None, cpu_count: Optional[Union[int, str]]=None, cpu_percent: Optional[Union[int, str]]=None,
                 nano_cpus: Optional[Union[int, str]]=None, cpuset_mems: Optional[str]=None, runtime: None=None, mounts: None=None,
                 cpu_rt_period: Optional[Union[int, str]]=None, cpu_rt_runtime: Optional[Union[int, str]]=None,
                 device_cgroup_rules: None=None, device_requests: Optional[List[Union[Dict[str, List[str]], Dict[str, Union[str, int, List[List[str]], Dict[str, str]]]]]]=None,
                 cgroupns: Optional[str]=None) -> None:

        if mem_limit is not None:
            self['Memory'] = parse_bytes(mem_limit)

        if memswap_limit is not None:
            self['MemorySwap'] = parse_bytes(memswap_limit)

        if mem_reservation:
            self['MemoryReservation'] = parse_bytes(mem_reservation)

        if kernel_memory:
            self['KernelMemory'] = parse_bytes(kernel_memory)

        if mem_swappiness is not None:
            if not isinstance(mem_swappiness, int):
                raise host_config_type_error(
                    'mem_swappiness', mem_swappiness, 'int'
                )

            self['MemorySwappiness'] = mem_swappiness

        if shm_size is not None:
            if isinstance(shm_size, str):
                shm_size = parse_bytes(shm_size)

            self['ShmSize'] = shm_size

        if pid_mode:
            if version_lt(version, '1.24') and pid_mode != 'host':
                raise host_config_value_error('pid_mode', pid_mode)
            self['PidMode'] = pid_mode

        if ipc_mode:
            self['IpcMode'] = ipc_mode

        if privileged:
            self['Privileged'] = privileged

        if oom_kill_disable:
            self['OomKillDisable'] = oom_kill_disable

        if oom_score_adj:
            if version_lt(version, '1.22'):
                raise host_config_version_error('oom_score_adj', '1.22')
            if not isinstance(oom_score_adj, int):
                raise host_config_type_error(
                    'oom_score_adj', oom_score_adj, 'int'
                )
            self['OomScoreAdj'] = oom_score_adj

        if publish_all_ports:
            self['PublishAllPorts'] = publish_all_ports

        if read_only is not None:
            self['ReadonlyRootfs'] = read_only

        if dns_search:
            self['DnsSearch'] = dns_search

        if network_mode == 'host' and port_bindings:
            raise host_config_incompatible_error(
                'network_mode', 'host', 'port_bindings'
            )
        self['NetworkMode'] = network_mode or 'default'

        if restart_policy:
            if not isinstance(restart_policy, dict):
                raise host_config_type_error(
                    'restart_policy', restart_policy, 'dict'
                )

            self['RestartPolicy'] = restart_policy

        if cap_add:
            self['CapAdd'] = cap_add

        if cap_drop:
            self['CapDrop'] = cap_drop

        if devices:
            self['Devices'] = parse_devices(devices)

        if group_add:
            self['GroupAdd'] = [str(grp) for grp in group_add]

        if dns is not None:
            self['Dns'] = dns

        if dns_opt is not None:
            self['DnsOptions'] = dns_opt

        if security_opt is not None:
            if not isinstance(security_opt, list):
                raise host_config_type_error(
                    'security_opt', security_opt, 'list'
                )

            self['SecurityOpt'] = security_opt

        if sysctls:
            if not isinstance(sysctls, dict):
                raise host_config_type_error('sysctls', sysctls, 'dict')
            self['Sysctls'] = {}
            for k, v in sysctls.items():
                self['Sysctls'][k] = str(v)

        if volumes_from is not None:
            if isinstance(volumes_from, str):
                volumes_from = volumes_from.split(',')

            self['VolumesFrom'] = volumes_from

        if binds is not None:
            self['Binds'] = convert_volume_binds(binds)

        if port_bindings is not None:
            self['PortBindings'] = convert_port_bindings(port_bindings)

        if extra_hosts is not None:
            if isinstance(extra_hosts, dict):
                extra_hosts = format_extra_hosts(extra_hosts)

            self['ExtraHosts'] = extra_hosts

        if links is not None:
            self['Links'] = normalize_links(links)

        if isinstance(lxc_conf, dict):
            formatted = []
            for k, v in lxc_conf.items():
                formatted.append({'Key': k, 'Value': str(v)})
            lxc_conf = formatted

        if lxc_conf is not None:
            self['LxcConf'] = lxc_conf

        if cgroup_parent is not None:
            self['CgroupParent'] = cgroup_parent

        if ulimits is not None:
            if not isinstance(ulimits, list):
                raise host_config_type_error('ulimits', ulimits, 'list')
            self['Ulimits'] = []
            for lmt in ulimits:
                if not isinstance(lmt, Ulimit):
                    lmt = Ulimit(**lmt)
                self['Ulimits'].append(lmt)

        if log_config is not None:
            if not isinstance(log_config, LogConfig):
                if not isinstance(log_config, dict):
                    raise host_config_type_error(
                        'log_config', log_config, 'LogConfig'
                    )
                log_config = LogConfig(**log_config)

            self['LogConfig'] = log_config

        if cpu_quota:
            if not isinstance(cpu_quota, int):
                raise host_config_type_error('cpu_quota', cpu_quota, 'int')
            self['CpuQuota'] = cpu_quota

        if cpu_period:
            if not isinstance(cpu_period, int):
                raise host_config_type_error('cpu_period', cpu_period, 'int')
            self['CpuPeriod'] = cpu_period

        if cpu_shares:
            if not isinstance(cpu_shares, int):
                raise host_config_type_error('cpu_shares', cpu_shares, 'int')

            self['CpuShares'] = cpu_shares

        if cpuset_cpus:
            self['CpusetCpus'] = cpuset_cpus

        if cpuset_mems:
            if not isinstance(cpuset_mems, str):
                raise host_config_type_error(
                    'cpuset_mems', cpuset_mems, 'str'
                )
            self['CpusetMems'] = cpuset_mems

        if cpu_rt_period:
            if version_lt(version, '1.25'):
                raise host_config_version_error('cpu_rt_period', '1.25')

            if not isinstance(cpu_rt_period, int):
                raise host_config_type_error(
                    'cpu_rt_period', cpu_rt_period, 'int'
                )
            self['CPURealtimePeriod'] = cpu_rt_period

        if cpu_rt_runtime:
            if version_lt(version, '1.25'):
                raise host_config_version_error('cpu_rt_runtime', '1.25')

            if not isinstance(cpu_rt_runtime, int):
                raise host_config_type_error(
                    'cpu_rt_runtime', cpu_rt_runtime, 'int'
                )
            self['CPURealtimeRuntime'] = cpu_rt_runtime

        if blkio_weight:
            if not isinstance(blkio_weight, int):
                raise host_config_type_error(
                    'blkio_weight', blkio_weight, 'int'
                )
            if version_lt(version, '1.22'):
                raise host_config_version_error('blkio_weight', '1.22')
            self["BlkioWeight"] = blkio_weight

        if blkio_weight_device:
            if not isinstance(blkio_weight_device, list):
                raise host_config_type_error(
                    'blkio_weight_device', blkio_weight_device, 'list'
                )
            if version_lt(version, '1.22'):
                raise host_config_version_error('blkio_weight_device', '1.22')
            self["BlkioWeightDevice"] = blkio_weight_device

        if device_read_bps:
            if not isinstance(device_read_bps, list):
                raise host_config_type_error(
                    'device_read_bps', device_read_bps, 'list'
                )
            if version_lt(version, '1.22'):
                raise host_config_version_error('device_read_bps', '1.22')
            self["BlkioDeviceReadBps"] = device_read_bps

        if device_write_bps:
            if not isinstance(device_write_bps, list):
                raise host_config_type_error(
                    'device_write_bps', device_write_bps, 'list'
                )
            if version_lt(version, '1.22'):
                raise host_config_version_error('device_write_bps', '1.22')
            self["BlkioDeviceWriteBps"] = device_write_bps

        if device_read_iops:
            if not isinstance(device_read_iops, list):
                raise host_config_type_error(
                    'device_read_iops', device_read_iops, 'list'
                )
            if version_lt(version, '1.22'):
                raise host_config_version_error('device_read_iops', '1.22')
            self["BlkioDeviceReadIOps"] = device_read_iops

        if device_write_iops:
            if not isinstance(device_write_iops, list):
                raise host_config_type_error(
                    'device_write_iops', device_write_iops, 'list'
                )
            if version_lt(version, '1.22'):
                raise host_config_version_error('device_write_iops', '1.22')
            self["BlkioDeviceWriteIOps"] = device_write_iops

        if tmpfs:
            if version_lt(version, '1.22'):
                raise host_config_version_error('tmpfs', '1.22')
            self["Tmpfs"] = convert_tmpfs_mounts(tmpfs)

        if userns_mode:
            if version_lt(version, '1.23'):
                raise host_config_version_error('userns_mode', '1.23')

            if userns_mode != "host":
                raise host_config_value_error("userns_mode", userns_mode)
            self['UsernsMode'] = userns_mode

        if uts_mode:
            if uts_mode != "host":
                raise host_config_value_error("uts_mode", uts_mode)
            self['UTSMode'] = uts_mode

        if pids_limit:
            if not isinstance(pids_limit, int):
                raise host_config_type_error('pids_limit', pids_limit, 'int')
            if version_lt(version, '1.23'):
                raise host_config_version_error('pids_limit', '1.23')
            self["PidsLimit"] = pids_limit

        if isolation:
            if not isinstance(isolation, str):
                raise host_config_type_error('isolation', isolation, 'string')
            if version_lt(version, '1.24'):
                raise host_config_version_error('isolation', '1.24')
            self['Isolation'] = isolation

        if auto_remove:
            if version_lt(version, '1.25'):
                raise host_config_version_error('auto_remove', '1.25')
            self['AutoRemove'] = auto_remove

        if storage_opt is not None:
            if version_lt(version, '1.24'):
                raise host_config_version_error('storage_opt', '1.24')
            self['StorageOpt'] = storage_opt

        if init is not None:
            if version_lt(version, '1.25'):
                raise host_config_version_error('init', '1.25')
            self['Init'] = init

        if init_path is not None:
            if version_lt(version, '1.25'):
                raise host_config_version_error('init_path', '1.25')

            if version_gte(version, '1.29'):
                # https://github.com/moby/moby/pull/32470
                raise host_config_version_error('init_path', '1.29', False)
            self['InitPath'] = init_path

        if volume_driver is not None:
            self['VolumeDriver'] = volume_driver

        if cpu_count:
            if not isinstance(cpu_count, int):
                raise host_config_type_error('cpu_count', cpu_count, 'int')
            if version_lt(version, '1.25'):
                raise host_config_version_error('cpu_count', '1.25')

            self['CpuCount'] = cpu_count

        if cpu_percent:
            if not isinstance(cpu_percent, int):
                raise host_config_type_error('cpu_percent', cpu_percent, 'int')
            if version_lt(version, '1.25'):
                raise host_config_version_error('cpu_percent', '1.25')

            self['CpuPercent'] = cpu_percent

        if nano_cpus:
            if not isinstance(nano_cpus, int):
                raise host_config_type_error('nano_cpus', nano_cpus, 'int')
            if version_lt(version, '1.25'):
                raise host_config_version_error('nano_cpus', '1.25')

            self['NanoCpus'] = nano_cpus

        if runtime:
            if version_lt(version, '1.25'):
                raise host_config_version_error('runtime', '1.25')
            self['Runtime'] = runtime

        if mounts is not None:
            if version_lt(version, '1.30'):
                raise host_config_version_error('mounts', '1.30')
            self['Mounts'] = mounts

        if device_cgroup_rules is not None:
            if version_lt(version, '1.28'):
                raise host_config_version_error('device_cgroup_rules', '1.28')
            if not isinstance(device_cgroup_rules, list):
                raise host_config_type_error(
                    'device_cgroup_rules', device_cgroup_rules, 'list'
                )
            self['DeviceCgroupRules'] = device_cgroup_rules

        if device_requests is not None:
            if version_lt(version, '1.40'):
                raise host_config_version_error('device_requests', '1.40')
            if not isinstance(device_requests, list):
                raise host_config_type_error(
                    'device_requests', device_requests, 'list'
                )
            self['DeviceRequests'] = []
            for req in device_requests:
                if not isinstance(req, DeviceRequest):
                    req = DeviceRequest(**req)
                self['DeviceRequests'].append(req)

        if cgroupns:
            self['CgroupnsMode'] = cgroupns


def host_config_type_error(param: str, param_value: Union[Dict[str, str], str, float], expected: str) -> TypeError:
    return TypeError(
        f'Invalid type for {param} param: expected {expected} '
        f'but found {type(param_value)}'
    )


def host_config_version_error(param: str, version: str, less_than: bool=True) -> InvalidVersion:
    operator = '<' if less_than else '>'
    return errors.InvalidVersion(
        f'{param} param is not supported in API versions {operator} {version}',
    )

def host_config_value_error(param: str, param_value: str) -> ValueError:
    return ValueError(f'Invalid value for {param} param: {param_value}')


def host_config_incompatible_error(param, param_value, incompatible_param):
    return errors.InvalidArgument(
        f'\"{param_value}\" {param} is incompatible with {incompatible_param}'
    )


class ContainerConfig(dict):
    def __init__(
        self, version: str, image: str, command: Union[str, List[str]], hostname: None=None, user: Optional[int]=None, detach: bool=False,
        stdin_open: bool=False, tty: bool=False, ports: Optional[List[Union[int, Tuple[int, str], Tuple[int]]]]=None, environment: Optional[List[str]]=None,
        volumes: Optional[List[str]]=None, network_disabled: bool=False, entrypoint: Optional[str]=None,
        working_dir: Optional[str]=None, domainname: None=None, host_config: Optional[HostConfig]=None, mac_address: Optional[str]=None,
        labels: Optional[Union[Dict[str, str], List[str]]]=None, stop_signal: Optional[str]=None, networking_config: Optional[NetworkingConfig]=None,
        healthcheck: None=None, stop_timeout: None=None, runtime: None=None
    ) -> None:

        if stop_timeout is not None and version_lt(version, '1.25'):
            raise errors.InvalidVersion(
                'stop_timeout was only introduced in API version 1.25'
            )

        if healthcheck is not None:
            if version_lt(version, '1.24'):
                raise errors.InvalidVersion(
                    'Health options were only introduced in API version 1.24'
                )

            if version_lt(version, '1.29') and 'StartPeriod' in healthcheck:
                raise errors.InvalidVersion(
                    'healthcheck start period was introduced in API '
                    'version 1.29'
                )

        if isinstance(command, str):
            command = split_command(command)

        if isinstance(entrypoint, str):
            entrypoint = split_command(entrypoint)

        if isinstance(environment, dict):
            environment = format_environment(environment)

        if isinstance(labels, list):
            labels = {lbl: '' for lbl in labels}

        if isinstance(ports, list):
            exposed_ports = {}
            for port_definition in ports:
                port = port_definition
                proto = 'tcp'
                if isinstance(port_definition, tuple):
                    if len(port_definition) == 2:
                        proto = port_definition[1]
                    port = port_definition[0]
                exposed_ports[f'{port}/{proto}'] = {}
            ports = exposed_ports

        if isinstance(volumes, str):
            volumes = [volumes, ]

        if isinstance(volumes, list):
            volumes_dict = {}
            for vol in volumes:
                volumes_dict[vol] = {}
            volumes = volumes_dict

        if healthcheck and isinstance(healthcheck, dict):
            healthcheck = Healthcheck(**healthcheck)

        attach_stdin = False
        attach_stdout = False
        attach_stderr = False
        stdin_once = False

        if not detach:
            attach_stdout = True
            attach_stderr = True

            if stdin_open:
                attach_stdin = True
                stdin_once = True

        self.update({
            'Hostname': hostname,
            'Domainname': domainname,
            'ExposedPorts': ports,
            'User': str(user) if user is not None else None,
            'Tty': tty,
            'OpenStdin': stdin_open,
            'StdinOnce': stdin_once,
            'AttachStdin': attach_stdin,
            'AttachStdout': attach_stdout,
            'AttachStderr': attach_stderr,
            'Env': environment,
            'Cmd': command,
            'Image': image,
            'Volumes': volumes,
            'NetworkDisabled': network_disabled,
            'Entrypoint': entrypoint,
            'WorkingDir': working_dir,
            'HostConfig': host_config,
            'NetworkingConfig': networking_config,
            'MacAddress': mac_address,
            'Labels': labels,
            'StopSignal': stop_signal,
            'Healthcheck': healthcheck,
            'StopTimeout': stop_timeout,
            'Runtime': runtime
        })
