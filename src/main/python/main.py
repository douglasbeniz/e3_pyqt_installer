#from fbs_runtime.application_context import ApplicationContext
from PyQt5.QtWidgets import QMainWindow, QApplication, QInputDialog, QLineEdit
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QEvent, Qt
from PyQt5.uic import loadUi

import sys, os
import urllib.request

class e3InstallerWindow(QMainWindow):
    pushPreviousClicked = pyqtSignal()
    pushNextClicked = pyqtSignal()
    pushQuitClicked = pyqtSignal()

    def pushPreviousClicked(self, reset=False):
        if reset:
            nextIndex = 0
        else:
            curIndex = self.tabInstallSteps.currentIndex()
            nextIndex = curIndex -1
        maxTabs = self.tabInstallSteps.count()

        # Changing the visible tab
        self.tabInstallSteps.setCurrentIndex(nextIndex)

        # Controls visibility
        if nextIndex == 0:
            self.pushPrevious.setEnabled(False)

        if nextIndex+1 < maxTabs:
            self.pushNext.setEnabled(True   )


    def pushNextClicked(self):
        curIndex = self.tabInstallSteps.currentIndex()
        nextIndex = curIndex +1
        maxTabs = self.tabInstallSteps.count()

        # Changing the visible tab
        self.tabInstallSteps.setCurrentIndex(nextIndex)

        # Controls visibility
        if nextIndex+1 == maxTabs:
            self.pushNext.setEnabled(False)

        if nextIndex > 0:
            self.pushPrevious.setEnabled(True)

        # process correspondent step
        self.processInstallationStep(nextIndex)

    def menuActionRepo(self):
        newRepo, confirmed = QInputDialog.getText(self, "EPICS installation via e3", "Enter the new repository URL to look at:", QLineEdit.Normal, self.defaultRepo)

        if (confirmed and newRepo and newRepo != self.defaultRepo):
            self.defaultRepo = str(newRepo)
            # force the user to re-start the process
            self.pushPreviousClicked(reset=True)

    def __init__(self):
        QMainWindow.__init__(self)

        # ---------------------------------------------------------------------
        # object attributes
        self.defaultRepo = "https://github.com/douglasbeniz/e3"
        # ---------------------------------------------------------------------
        # loading the main form
        loadUi(os.path.dirname(__file__) + '/../forms/main.ui', self)

        # ---------------------------------------------------------------------
        # connecting signals and form components
        self.pushPrevious.clicked.connect(self.pushPreviousClicked)
        self.pushNext.clicked.connect(self.pushNextClicked)
        self.pushQuit.clicked.connect(self.close)
        self.actionRepo.triggered.connect(self.menuActionRepo)
        # ---------------------------------------------------------------------
        # connecting slots and form components
        self.tabInstallSteps.currentChanged.connect(self.updateSelectedTab)
        # ---------------------------------------------------------------------
        # configuring envent filter for tab
        self.tabInstallSteps.tabBar().installEventFilter(self)


    @pyqtSlot(int)
    def updateSelectedTab(self, val):
        #print("New selected tab: %d" % val)
        pass


    def eventFilter(self, object, event): 
        if object == self.tabInstallSteps.tabBar() and \
            ((event.type() in [QEvent.KeyPress, QEvent.KeyRelease] and event.key() in [Qt.LeftArrow, Qt.RightArrow, Qt.Key_Left, Qt.Key_Right, Qt.Key_Direction_L, Qt.Key_Direction_R]) or \
             (event.type() in [QEvent.MouseButtonPress, QEvent.MouseButtonRelease] and event.button() == Qt.LeftButton)):
            # Prevent user to navigate between tabs using mouse and keyboard...
            event.ignore()
            return True
        else:
            return super(e3InstallerWindow, self).eventFilter(object, event)

    def processInstallationStep(self, step):
        "https://github.com/douglasbeniz/e3/raw/master/LICENSE"
        if step == 0:       # main
            pass
        elif step == 1:     # license
            try:
                response = urllib.request.urlopen('%s//%s' % (self.defaultRepo,'raw/master/LICENSE'))
                licenseText = response.read()
                # if that was fine, show it
                #self.textLicense.setText(self, bytes(str(licenseText), 'utf-8'))
                self.textEdit.setText(self.HTMLsafe(licenseText))
                #self.textLicense.setSource(self, '%s//%s' % (self.defaultRepo,'raw/master/LICENSE'))
            except Exception as e:
                raise e
        elif step == 2:     # versions
            pass
        elif step == 3:     # modules
            pass
        elif step == 4:     # target
            pass

if __name__ == '__main__':
    app = QApplication(sys.argv)
    #win = uic.loadUi(os.path.dirname(__file__) + '/../forms/main.ui')
    #win.show()
    mainWin = e3InstallerWindow()
    mainWin.show()
    # wait until the window is closed...
    sys.exit(app.exec_())