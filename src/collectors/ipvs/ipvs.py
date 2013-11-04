# coding=utf-8

"""
Shells out to get ipvs statistics, which may or may not require sudo access

#### Dependencies

 * /usr/sbin/ipvsadmin

"""

import diamond.collector
import subprocess
import os
import string
from diamond.collector import str_to_bool


class IPVSCollector(diamond.collector.Collector):

    def __init__(self, config, handlers):
        super(IPVSCollector, self).__init__(config, handlers)

        # Verify the --exact flag works
        self.command = [self.config['bin'], '--list', '--stats', '--numeric',
                        '--exact']

        if str_to_bool(self.config['use_sudo']):
            self.command.insert(0, self.config['sudo_cmd'])
            # The -n (non-interactive) option prevents sudo from
            # prompting the user for a password.
            self.command.insert(1, '-n')

        p = subprocess.Popen(self.command, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        p.wait()

        if p.returncode == 255:
            self.command = filter(lambda a: a != '--exact', self.command)

    def get_default_config_help(self):
        config_help = super(IPVSCollector, self).get_default_config_help()
        config_help.update({
            'bin': 'Path to ipvsadm binary',
            'use_sudo': 'Use sudo?',
            'sudo_cmd': 'Path to sudo',
        })
        return config_help

    def get_default_config(self):
        """
        Returns the default collector settings
        """
        config = super(IPVSCollector, self).get_default_config()
        config.update({
            'bin':              '/usr/sbin/ipvsadm',
            'use_sudo':         True,
            'sudo_cmd':         '/usr/bin/sudo',
            'path':             'ipvs'
        })
        return config

    def collect(self):
        if not os.access(self.config['bin'], os.X_OK):
            self.log.error("%s is not executable", self.config['bin'])
            return False

        if (str_to_bool(self.config['use_sudo'])
            and not os.access(self.config['sudo_cmd'], os.X_OK)):
            self.log.error("%s is not executable", self.config['sudo_cmd'])
            return False

        p = subprocess.Popen(self.command,
                             stdout=subprocess.PIPE).communicate()[0][:-1]

        columns = {
            'conns': 2,
            'inpkts': 3,
            'outpkts': 4,
            'inbytes': 5,
            'outbytes': 6,
        }

        external = ""
        backend = ""
        for i, line in enumerate(p.split("\n")):
            if i < 3:
                continue
            row = line.split()

            if row[0] == "TCP" or row[0] == "UDP":
                external = string.replace(row[1], ".", "_")
                backend = "total"
            elif row[0] == "->":
                backend = string.replace(row[1], ".", "_")
            else:
                continue

            for metric, column in columns.iteritems():
                metric_name = ".".join([external, backend, metric])
                # metric_value = int(row[column])
                value = row[column]
                if (value.endswith('K')):
                        metric_value = int(value[0:len(value) - 1]) * 1024
                elif (value.endswith('M')):
                        metric_value = (int(value[0:len(value) - 1]) * 1024
                                        * 1024)
                elif (value.endswith('G')):
                        metric_value = (int(value[0:len(value) - 1]) * 1024.0
                                        * 1024.0 * 1024.0)
                else:
                        metric_value = float(value)

                self.publish(metric_name, metric_value)
