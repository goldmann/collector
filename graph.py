import datetime
import StringIO
import matplotlib as mpl

from flask import current_app as app

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.dates import AutoDateFormatter
from matplotlib.dates import AutoDateLocator

from reading import Reading
from database import db_session
from utils import Timer

from werkzeug.exceptions import NotFound, BadRequest

import time
from time import strftime

from sqlalchemy.sql.expression import *

import numpy

class Graph:
   
    def __init__(self, readings):
        self.data = []

        for r in readings:
            self.data.append([r[0], r[1]])

        # Default color for line is purple
        self.color = 'purple'

        # Default color for background is white
        self.background_color = 'white'

        # Default width for line is 2
        self.width = 2

        # Should the graph occypt whole viewport?
        self.maximize = False

        # Do we want to see label on X axe?
        self.xlabel = False

        # Do we want to see label on Y axe?
        self.ylabel = True

        self.fig = None
 
    def set_color(self, color):
        if color in ['purple', 'red']:
            self.color = color

    def set_maximize(self, maximize):
        self.maximize = maximize

    def smooth(self, x, window_len=11, window='hanning'):

        if len(x) < window_len:
            raise ValueError, "Input vector needs to be bigger than window size."


        if window_len<3:
            return x


        if not window in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']:
            raise ValueError, "Window is on of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'"


        s=numpy.r_[x[window_len-1:0:-1],x,x[-1:-window_len:-1]]
        #print(len(s))
        if window == 'flat': #moving average
            w=numpy.ones(window_len,'d')
        else:
            w=eval('numpy.'+window+'(window_len)')

        y=numpy.convolve(w/w.sum(),s,mode='valid')
        return y

    def build(self):
        app.logger.info("Generating new graph...")

        app.logger.debug("Configuring the graph...")

        font = {'size': 14}

        mpl.rc('font', **font)
        mpl.rcParams['lines.linewidth'] = 2
        mpl.rcParams['figure.figsize'] = 10, 5
        mpl.rcParams['figure.dpi'] = 100

        self.fig = Figure(facecolor = self.background_color)

        if self.maximize:
            ax = self.fig.add_axes((0, 0, 1, 1))

            # Put the labels on the inside of the graph
            # when plotting a maximized graph


            yticks = ax.yaxis.get_major_ticks()

#            for t in yticks[-2:]
#                t.label.set_visible(False)

#            yticks[-1].label.set_visible(False)
#            yticks[0].label.set_visible(False)

            for tick in yticks:
                tick.set_pad(-22)

            for tick in ax.xaxis.get_major_ticks():
                tick.set_pad(-25)

        else:
            ax = self.fig.add_axes((0.08, 0.1, 0.9, 0.85))

            if self.ylabel:
                ax.set_ylabel('C')

            if self.xlabel:
                ax.set_xlabel('Date')

        ax.tick_params(axis='both', which='major', labelsize=9)

        x=[]
        y=[]

        for r in self.data:
            x.append(datetime.datetime.fromtimestamp(r[0]))
            y.append(r[1])


        adl = AutoDateLocator()
        myformatter = AutoDateFormatter(adl)

        ax.xaxis.set_major_locator(adl)
        ax.xaxis.set_major_formatter(myformatter)

        ax.grid(True)

        myformatter.scaled = {
            365.0 : '%Y',           # view interval > 356 days
            30. : '%b %Y',          # view interval > 30 days but less than 365 days
            1.0 : '%b %d',          # view interval > 1 day but less than 30 days
            1./24. : '%H:%M',       # view interval > 1 hour but less than 24 hours
            1./24./60. : '%M:%S',   # view interval > 1 min but less than 1 hour
            1./24./60./60. : '%S',  # view interval < 1 min
        }

        c = list(self.smooth(y, 9, 'blackman'))

        remove_count = len(c) - len(y)
        del c[0:remove_count/2]
        del c[len(c)-remove_count/2:len(c)]

        with Timer() as duration:
            ax.plot(x, y, 'o', antialiased = True, color = 'black', alpha = 0.2)
            ax.plot(x, c, '-', antialiased = True, color = self.color, alpha = 1)

        app.logger.debug("Ploting a graph took %d ms", duration.miliseconds())

#        if self.maximize:
            # Hide first and last label on both axes
#            ax.get_xticklabels()[0].set_visible(False)
#            ax.get_xticklabels()[-1].set_visible(False)
#            ax.get_yticklabels()[0].set_visible(False)
#            ax.get_yticklabels()[-1].set_visible(False)

        self.fig.autofmt_xdate()

        return self

    def render(self, t = 'png'):
        canvas = FigureCanvas(self.fig)
        output = StringIO.StringIO()

        with Timer() as duration:
            if t == 'svg':
                canvas.print_svg(output)
            if t == 'pdf':
                canvas.print_pdf(output)
            else:
                canvas.print_png(output)

        app.logger.debug("Generating %s took %d ms", t.upper(), duration.miliseconds())

        return output.getvalue()
 
