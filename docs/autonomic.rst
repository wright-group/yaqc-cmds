Autonomic
---------

The autonomic system introduces a system of offsets for hardware.
Each offset has a control hardware (the independent variable) and an offset hardware (the dependent variable).
Each hardware can be offset by multiple control hardwares, and offsets always add.
The autonomic system plugs into ``attune``'s store.
Each hardware that ``yaqc-cmds`` sees will automatically have an ``attune`` instrument created with the name ``autotune_<offset_hardware_name>``.
Within this, an arrangement for each control hardware is created.
By default, this arrangement contains one tune with the name ``auto``.
However if the control hardware also appears in the ``attune`` store a different tune will be created for each control hardware arrangement.
