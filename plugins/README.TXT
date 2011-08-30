This directory contains plugins for various larch uses

Plugins should be not placed in this directory, but in
subdirectories, which should be arranged based on
application-specific needs.

On startup, the larch interpreter will look in selected
subdirectories for plugin modules, and plug them into.

Plugins in the 'std' folder will always be loaded, all
others are configured per application.

The wx folder contains plugins that need to be running
in a wx-enabled environment.

