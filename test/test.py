# test_pyqtgraph.py

from PySide6.QtWidgets import QApplication
import pyqtgraph as pg

app = QApplication([])

plot = pg.PlotWidget()

plot.plot(
    [0,1,2,3],
    [0,1,0,1]
)

plot.show()

app.exec()