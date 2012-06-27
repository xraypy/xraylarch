=======================================================
Tutorial: Plotting and Displaying Data
=======================================================

Plotting and Visualizing data are vital to any scientific analysis package,
and Larch provides several methods for data visualization.  These are
largely built on two types of data display.  The first is the line plot
(sometimes calld an xy plot), which shows traces of a set of functions
y(x).  The second type of data display supported is the 2-dimensional image
display, in which a grey scale or false color map shows an image
representing a 2-dimensional array of intensity.

Though not as fancy as many dedicated plotting and graphics packages, Larch
attempts to provide satisfying and graphical displays of data, and the
basic plots made with Larch can be high enough quality to include in
publications.  In addition, both line plots and image display provide
interactive features such as zooming in and out, changing properties such
as colors and labels.  Finally, copying and saving images of the graphics
is easy and can be done either with keyboard commands such as Ctrl-C or
from dropdown menus on the graphic elements.


Line Plots
==============

Larch provides a few functions for making line plots, with the principle
function being called :func:`plot`.  The :func:`plot` function takes two
arrays: `x`, the abscissa array, and `y`, the ordinate array.  It also
accepts a very large number of optional arguments for setting properties
like color, line style, labels, and so on.  Most of these properties can
also be set after the plot is displayed through the graphical display of
the plot itself.

Multiple plot windows can be shown simultaneously and you can easily
control which one to draw to.


.. function:: plot(x, y, **kws)

   Plot y(x) given 1-dimensional x and y arrays -- these must be of the
   same size.   Each x-y pair  displayed  is called a *trace*.  
   There are many optional keyword/value parameters, and given in the 
   :ref:`Table of Plot Arguments <plotopt_table>` below.

.. function:: newplot(x, y, **kws)

   This is essentially the same a :func:`plot`, but with the option  `new=True`.
   The rest of the arguments are as listed in  :ref:`Table of Plot Arguments <plotopt_table>`.

.. function:: scatterplot(x, y, **kws)

   A scatterplot differs from a line plot in that the set of x, y values
   are not assumed to be in any particular order, and so are not connected
   with a line.  Arguments are very similar to those for :func:`plot`, and
   are listed in  :ref:`Table of Plot Arguments <plotopt_table>`.

.. _plotopt_table:

**Table of Plot Arguments** These arguments apply for the :meth:`plot`, :meth:`newplot`, and
:meth:`scatterplot` methods.  Except where noted, the arguments are available for :meth:`plot` and
:meth:`newplot`.  In addition, the :meth:`scatterplot` method uses many of the same arguments for the
same meaning, as indicated by the right-most column.

  +-------------+------------+---------+------------------------------------------------+-------------+
  | argument    |   type     | default | meaning                                        | scatterplot?|
  +=============+============+=========+================================================+=============+
  | title       | string     | None    | Plot title                                     |  yes        |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | ylabel      | string     | None    | abscissa label                                 |  yes        |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | y2label     | string     | None    | right-hand abscissa label                      |  yes        |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | label       | string     | None    | trace label (defaults to 'trace N')            |  yes        |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | side        | left/right | left    | side for y-axis and label                      |  yes        |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | grid        | None/bool  | None    | to show grid lines                             |  yes        |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | color       | string     | blue    | color to use for trace                         |  yes        |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | use_dates   | bool       | False   | to show dates in xlabel (:meth:`plot` only)    |  no         |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | linewidth   | int        | 2       | linewidth for trace                            |  no         |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | style       | string     | solid   | line-style for trace (solid, dashed, ...)      |  no         |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | drawstyle   | string     | line    | style connecting points of trace               |  no         |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | marker      | string     | None    | symbol to show for each point (+, o, ....)     |  no         |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | markersize  | int        | 8       | size of marker shown for each point            |  no         |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | dy          | array      | None    | uncertainties for y values; error bars         |  no         |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | ylog_scale  | bool       | False   | draw y axis with log(base 10) scale            |  no         |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | xmin        | float      | None    | minimum displayed x value                      |  yes        |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | xmax        | float      | None    | maximum displayed x value                      |  yes        |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | ymin        | float      | None    | minimum displayed y value                      |  yes        |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | ymax        | float      | None    | maximum displayed y value                      |  yes        |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | autoscale   | bool       | True    | whether to automatically set plot limits       |  no         |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | draw_legend | None/bool  | None    | whether to display legend (None: leave as is)  |  no         |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | refresh     | bool       | True    | whether to refresh display                     |  no         |
  +-------------+------------+---------+------------------------------------------------+-------------+
  |             | **arguments that apply only for** :meth:`scatterplot`                 |             |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | size        | int        | 10      | size of marker                                 |  yes        |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | edgecolor   | string     | black   | edge color of marker                           |  yes        |
  +-------------+------------+---------+------------------------------------------------+-------------+
  | selectcolor | string     | red     | color for selected points                      |  yes        |
  +-------------+------------+---------+------------------------------------------------+-------------+

  For each plot window, the configuration for the plot (title, labels, grid
  displays, etc) and the properties of each trace (color, linewidth, ...)
  are preserved for the duration of that window.   A few specific notes:

   1. The title, label, and grid arguments to :func:`plot` default to ``None``,
   which means to use the previously used value.

   2. The *use_dates* option is not very rich, and simply turns x-values that
   are Unix timestamps into x labels showing the dates.

   3. While the default is to auto-scale the plot from the data ranges,
   specifying any of the limits will override the corresponding limit(s).

   4. The *color* argument can be any color name ("blue", "red", "black", etc),
   standard X11 color names ("cadetblue3", "darkgreen", etc), or an RGB hex
   color string of the form "#RRGGBB".

   5. Valid *style* arguments are 'solid', 'dashed', 'dotted', or 'dash-dot',
   with 'solid' as the default.

   6. Valid *marker* arguments are '+', 'o', 'x', '^', 'v', '>', '<', '|', '_',
   'square', 'diamond', 'thin diamond', 'hexagon', 'pentagon', 'tripod 1', or
   'tripod 2'.

   7. Valid *drawstyles* are None (which connects points with a straight line),
   'steps-pre', 'steps-mid', or 'steps-post', which give a step between the
   points, either just after a point ('steps-pre'), midway between them
   ('steps-mid') or just before each point ('steps-post').   Note that if displaying
   discrete values as a function of time, left-to-right, and want to show a
   transition to a new value as a sudden step, you want 'steps-post'.

  Again, most of theese values can be configured interactively from the  plot window.

.. method:: update_line(x, y, trace, side='left')

   updates an existing trace.

   :param x:     array of x values
   :param y:     array of y values
   :param trace: integer index for the trace (1 is the first trace)
   :param side:  which y axis to use ('left' or 'right').

   This function is particularly useful for data that is changing and you
   wish to update traces from a previous :func:`plot` with new (x, y) data
   without completely redrawing the entire plot.  Using this method is
   substantially faster than replotting, and should be used for dynamic
   plots, such as those happening during fits.



Image Display
===============
