#!/usr/bin/env python
"""
Written by Nathan Prziborowski
Github: https://github.com/prziborowski

This code is released under the terms of the Apache 2
http://www.apache.org/licenses/LICENSE-2.0.html

Example script shows how to add a virtual CD-ROM device to a VM,
using a physical device and an iso path and removing the device.

"""
import sys
from pyVmomi import vim
from pyVim.task import WaitForTask
from tools import cli, service_instance

__author__ = 'prziborowski'

# Prerequisite for VM (for simplicity sake)
# is there is an existing IDE controller.


def get_dc(si, name):
    for dc in si.content.rootFolder.childEntity:
        if dc.name == name:
            return dc
    raise Exception('Failed to find datacenter named %s' % name)


# Returns the first cdrom if any, else None.
def get_physical_cdrom(host):
    for lun in host.configManager.storageSystem.storageDeviceInfo.scsiLun:
        if lun.lunType == 'cdrom':
            return lun
    return None


def find_free_ide_controller(vm):
    for dev in vm.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualIDEController):
            # If there are less than 2 devices attached, we can use it.
            if len(dev.device) < 2:
                return dev
    return None


def find_device(vm, device_type):
    result = []
    for dev in vm.config.hardware.device:
        if isinstance(dev, device_type):
            result.append(dev)
    return result


def new_cdrom_spec(controller_key, backing):
    connectable = vim.vm.device.VirtualDevice.ConnectInfo()
    connectable.allowGuestControl = True
    connectable.startConnected = True

    cdrom = vim.vm.device.VirtualCdrom()
    cdrom.controllerKey = controller_key
    cdrom.key = -1
    cdrom.connectable = connectable
    cdrom.backing = backing
    return cdrom


def main():
    parser = cli.Parser()
    parser.add_required_arguments(cli.Argument.VM_NAME, cli.Argument.ISO)
    parser.add_optional_arguments(cli.Argument.DATACENTER_NAME)
    args = parser.get_args()
    serviceInstance = service_instance.connect(args)
    if args.datacenter_name:
        dc = get_dc(serviceInstance, args.datacenter_name)
    else:
        dc = serviceInstance.content.rootFolder.childEntity[0]

    vm = serviceInstance.content.searchIndex.FindChild(dc.vmFolder, args.vm_name)
    if vm is None:
        raise Exception('Failed to find VM %s in datacenter %s' %
                        (args.vm_name, dc.name))

    controller = find_free_ide_controller(vm)
    if controller is None:
        raise Exception('Failed to find a free slot on the IDE controller')

    cdrom = None

    cdrom_lun = get_physical_cdrom(vm.runtime.host)
    if cdrom_lun is not None:
        backing = vim.vm.device.VirtualCdrom.AtapiBackingInfo()
        backing.deviceName = cdrom_lun.deviceName
        deviceSpec = vim.vm.device.VirtualDeviceSpec()
        deviceSpec.device = new_cdrom_spec(controller.key, backing)
        deviceSpec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        configSpec = vim.vm.ConfigSpec(deviceChange=[deviceSpec])
        WaitForTask(vm.Reconfigure(configSpec))

        cdroms = find_device(vm, vim.vm.device.VirtualCdrom)
        cdrom = next(filter(lambda x: type(x.backing) == type(backing) and
                       x.backing.deviceName == cdrom_lun.deviceName,
                       cdroms))
    else:
        print('Skipping physical CD-Rom test as no device present.')

    op = vim.vm.device.VirtualDeviceSpec.Operation
    iso = args.iso
    if iso is not None:
        deviceSpec = vim.vm.device.VirtualDeviceSpec()
        if cdrom is None:  # add a cdrom
            backing = vim.vm.device.VirtualCdrom.IsoBackingInfo(fileName=iso)
            cdrom = new_cdrom_spec(controller.key, backing)
            deviceSpec.operation = op.add
        else:  # edit an existing cdrom
            backing = vim.vm.device.VirtualCdrom.IsoBackingInfo(fileName=iso)
            cdrom.backing = backing
            deviceSpec.operation = op.edit
        deviceSpec.device = cdrom
        configSpec = vim.vm.ConfigSpec(deviceChange=[deviceSpec])
        WaitForTask(vm.Reconfigure(configSpec))

        cdroms = find_device(vm, vim.vm.device.VirtualCdrom)
        cdrom = next(filter(lambda x: type(x.backing) == type(backing) and
                       x.backing.fileName == iso, cdroms))
    else:
        print('Skipping ISO test as no iso provided.')

    if cdrom is not None:  # Remove it
        deviceSpec = vim.vm.device.VirtualDeviceSpec()
        deviceSpec.device = cdrom
        deviceSpec.operation = op.remove
        configSpec = vim.vm.ConfigSpec(deviceChange=[deviceSpec])
        WaitForTask(vm.Reconfigure(configSpec))

if __name__ == '__main__':
    main()
