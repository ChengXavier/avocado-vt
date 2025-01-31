"""
Module simplifying manipulation of the vm attributes described at
http://libvirt.org/formatdomain.html
"""


import logging
import re

from avocado.core import exceptions

from virttest import virsh
from virttest.libvirt_xml import vm_xml
from virttest.libvirt_xml.devices import controller
from virttest.libvirt_xml.devices import channel
from virttest.libvirt_xml.devices import disk
from virttest.libvirt_xml.devices import hostdev
from virttest.libvirt_xml.devices import interface
from virttest.libvirt_xml.devices import rng
from virttest.libvirt_xml.devices import serial
from virttest.libvirt_xml.devices import vsock
from virttest.libvirt_xml.devices import watchdog
from virttest.utils_test import libvirt

LOG = logging.getLogger('avocado.' + __name__)


def set_vm_attrs(vmxml, vm_attrs):
    """
    Set element/value pairs in VMXML instance

    :param vmxml: VMXML instance of the domain
    :param vm_attrs: dict of the attribute/value pairs in VMXML
    :return the updated vmxml
    """
    for attr, value in list(vm_attrs.items()):
        LOG.debug('Set %s = %s', attr, value)
        setattr(vmxml, attr, int(value) if value.isdigit() else value)
    vmxml.xmltreefile.write()
    vmxml.sync()
    return vmxml


def check_guest_xml(vm_name, pat_in_dumpxml, option='', status_error=False):
    """
    Check the given pattern in the vm dumpxml

    :param vm_name: vm name
    :param pat_in_dumpxml:  str, the pattern to search in dumpxml
    :param option: str, extra options for dumpxml command
    :param status_error: True if expect not existing, otherwise False
    :raises: TestFail if the result is not expected
    """
    ret_stdout = virsh.dumpxml(vm_name, extra=option).stdout.strip()
    match = re.search(pat_in_dumpxml, ret_stdout)
    found = True if match else False
    prefix_found = '' if found else 'not '
    msg = "The pattern '%s' is %sfound in the vm dumpxml" % (pat_in_dumpxml, prefix_found)
    if found ^ status_error:
        LOG.debug(msg)
    else:
        raise exceptions.TestFail(msg)


def remove_vm_devices_by_type(vm, device_type):
    """
    Remove devices of a given type.

    :param vm: The vm object.
    :param device_type: Type of devices should be removed.
    """
    vm_was_running = vm.is_alive()
    vmxml = vm_xml.VMXML.new_from_dumpxml(vm.name)
    vmxml.remove_all_device_by_type(device_type)
    vmxml.sync()

    if vm_was_running:
        vm.start()


def create_vm_device_by_type(dev_type, dev_dict):
    """
    Create device by device type

    :param dev_type: device type
    :param dev_dict: dict for device
    :return: device object
    """
    dev_obj = None
    if dev_type == 'disk':
        dev_obj = disk.Disk()
    elif dev_type == 'controller':
        dev_obj = controller.Controller()
    elif dev_type == 'interface':
        dev_obj = interface.Interface()
    elif dev_type == 'channel':
        dev_obj = channel.Channel()
    elif dev_type == 'serial':
        dev_obj = serial.Serial()
    elif dev_type == 'vsock':
        dev_obj = vsock.Vsock()
    elif dev_type == 'watchdog':
        dev_obj = watchdog.Watchdog()
    elif dev_type == 'rng':
        dev_obj = rng.Rng()
    elif dev_type == 'hostdev':
        dev_obj = hostdev.Hostdev()

    dev_obj.setup_attrs(**dev_dict)

    return dev_obj


def modify_vm_device(vmxml, dev_type, dev_dict=None, index=0):
    """
     Get specified device , update it with given dev_dict if the device exists,
     Create the device if it does not exist

    :param vmxml: domain VMXML instance
    :param dev_type: device type
    :param dev_dict: dict to create device
    :param index: device index
    :return: device object
    """
    dev_obj = None
    try:
        dev_obj, xml_devices = libvirt.get_vm_device(vmxml, dev_type, index=index)
        dev_obj.setup_attrs(**dev_dict)

        vmxml.devices = xml_devices
        vmxml.xmltreefile.write()
        vmxml.sync()
    except IndexError:
        dev_obj = create_vm_device_by_type(dev_type, dev_dict)
        libvirt.add_vm_device(vmxml, dev_obj)

    return dev_obj
