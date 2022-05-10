#!/usr/bin/env python
# Author: Samuel Krieg
"""
Example setting a custom attribute on a VM
"""

from pyVmomi import vim
from tools import cli, service_instance, pchelper


def get_vm(si, content, args):
    """ Return the VM specified in args
    """
    vm = None
    if args.uuid:
        search_index = si.content.searchIndex
        vm = search_index.FindByUuid(None, args.uuid, True)
    elif args.vm_name:
        vm = pchelper.get_obj(content, [vim.VirtualMachine], args.vm_name)
    return vm


def set_vm_attribute(vm, manager, field_name, field_value):
    """ Set the custom attribute to the VM

        Create the attribute if it does not exist.
    """
    for field in manager.field:
        if field.name == field_name:
            manager.SetField(entity=vm, key=field.key, value=field_value)
            return True

    raise SystemExit('Attribute %s not found' % field_name)
    # the attribute does not exist: create it
    # create custom attribute system wide
    #manager.AddCustomFieldDef(name = field_name, moType = vim.VirtualMachine)
    #set_vm_attribute(vm, manager, field_name, field_value)


def main():
    parser = cli.Parser()
    parser.add_optional_arguments(cli.Argument.UUID, cli.Argument.VM_NAME)
    parser.add_custom_argument('-n', '--name', required=True, help='Name of the attribute.')
    parser.add_custom_argument('-V', '--value', required=True, help='Value of the attribute.')
    args = parser.get_args()
    si = service_instance.connect(args)
    content = si.RetrieveContent()
    try:
        vm = get_vm(si, content, args)
    except RuntimeError as e:
        raise SystemExit("ERROR: %s" % e)

    if not vm:
        raise SystemExit("Unable to locate VirtualMachine.")

    manager = content.customFieldsManager
    set_vm_attribute(vm, manager, args.name, args.value)


if __name__ == "__main__":
    main()
