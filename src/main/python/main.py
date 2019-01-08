#from fbs_runtime.application_context import ApplicationContext
from PyQt5.QtWidgets import QMainWindow, QApplication
from PyQt5.QtCore import pyqtSlot, pyqtSignal
from PyQt5.uic import loadUi

from PyQt5 import QtCore

import sys, os

class e3InstallerWindow(QMainWindow):
    pushPreviousClicked = pyqtSignal()
    pushNextClicked = pyqtSignal()
    pushQuitClicked = pyqtSignal()

    def pushPreviousClicked(self):
        curIndex = self.tabInstallSteps.currentIndex()
        print("curIndex: %d" % curIndex)
        nextIndex = curIndex -1
        maxTabs = self.tabInstallSteps.count()
        print("maxTabs: %d" % maxTabs)

        # Changing the visible tab
        if nextIndex >= 0:
            self.tabInstallSteps.setCurrentIndex(nextIndex)
        else:
            print("it is the first tab!")

        # Controls visibility
        if nextIndex == 0:
            self.pushPrevious.setEnabled(False)

        if nextIndex+1 < maxTabs:
            self.pushNext.setEnabled(True   )


    def pushNextClicked(self):
        curIndex = self.tabInstallSteps.currentIndex()
        print("curIndex: %d" % curIndex)
        nextIndex = curIndex +1
        maxTabs = self.tabInstallSteps.count()
        print("maxTabs: %d" % maxTabs)

        # Changing the visible tab
        if nextIndex < maxTabs:
            self.tabInstallSteps.setCurrentIndex(nextIndex)
        else:
            print("it is the last tab!")

        # Controls visibility
        if nextIndex+1 == maxTabs:
            self.pushNext.setEnabled(False)

        if nextIndex > 0:
            self.pushPrevious.setEnabled(True)


    def __init__(self):
        QMainWindow.__init__(self)

        # loading the main form
        loadUi(os.path.dirname(__file__) + '/../forms/main.ui', self)

        # connecting signals and form components
        self.pushPrevious.clicked.connect(self.pushPreviousClicked)
        self.pushNext.clicked.connect(self.pushNextClicked)
        self.pushQuit.clicked.connect(self.close)
        # connecting slots and form components
        self.tabInstallSteps.currentChanged.connect(self.updateSelectedTab)
        self.tabInstallSteps.tabBar().installEventFilter(self)

    @pyqtSlot(int)
    def updateSelectedTab(self, val):
        print("New selected tab: %d" % val)


    def eventFilter(self, object, event): 
        if object == self.tabInstallSteps.tabBar() and \
            ((event.type() in [QtCore.QEvent.KeyPress, QtCore.QEvent.KeyRelease] and event.key() in [QtCore.Qt.LeftArrow, QtCore.Qt.RightArrow, QtCore.Qt.Key_Left, QtCore.Qt.Key_Right, QtCore.Qt.Key_Direction_L, QtCore.Qt.Key_Direction_R]) or \
             (event.type() in [QtCore.QEvent.MouseButtonPress, QtCore.QEvent.MouseButtonRelease] and event.button() == QtCore.Qt.LeftButton)):
            # Prevent user to navigate between tabs using mouse and keyboard...
            event.ignore()
            return True
        else:
            return super(e3InstallerWindow, self).eventFilter(object, event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    #win = uic.loadUi(os.path.dirname(__file__) + '/../forms/main.ui')
    #win.show()
    mainWin = e3InstallerWindow()
    mainWin.show()
    # wait until the window is closed...
    sys.exit(app.exec_())