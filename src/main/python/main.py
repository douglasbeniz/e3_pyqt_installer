#from fbs_runtime.application_context import ApplicationContext
from PyQt5.QtWidgets import QMainWindow, QApplication, QInputDialog, QLineEdit
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QEvent, Qt
from PyQt5.uic import loadUi

import sys, os
import requests

REQUIRE_ESS_REPO            = 'https://github.com/icshwi/require-ess/releases'
REQUIRE_ESS_REPO_API_TAGS   = 'https://api.github.com/repos/icshwi/require-ess/tags'
EPICS_BASE_REPO_API_TAGS    = 'https://api.github.com/repos/epics-base/epics-base/tags'

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
            nextEnabled = ((nextIndex == 0) or self.agrementAccepted)
            #self.pushNext.setEnabled(True)
            self.pushNext.setEnabled(nextEnabled)


    def pushNextClicked(self):
        curIndex = self.tabInstallSteps.currentIndex()
        nextIndex = curIndex +1
        maxTabs = self.tabInstallSteps.count()

        # Changing the visible tab
        self.tabInstallSteps.setCurrentIndex(nextIndex)

        # Controls visibility
        if nextIndex+1 == maxTabs:
            #self.pushNext.setEnabled(False)
            self.pushNext.setEnabled(False)
        else:
            nextEnabled = self.agrementAccepted
            self.pushNext.setEnabled(nextEnabled)

        if nextIndex > 0:
            self.pushPrevious.setEnabled(True)

        if nextIndex == 3:
            print(self.requireVersion)
            print(self.baseVersion)

        # process correspondent step
        self.processInstallationStep(nextIndex)


    def menuActionRepo(self):
        newRepo, confirmed = QInputDialog.getText(self, "EPICS installation via e3", "Enter the new repository URL to look at:", QLineEdit.Normal, self.defaultRepo)

        if (confirmed and newRepo and newRepo != self.defaultRepo):
            self.defaultRepo = str(newRepo)
            # Clear list of versions
            self.lstBase.clear()
            self.lstRequire.clear()
            # Reset license acceptance
            self.agrementAccepted = False
            self.checkAgree.setCheckState(Qt.Unchecked)
            # force the user to re-start the process
            self.pushPreviousClicked(reset=True)


    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)

        # ---------------------------------------------------------------------
        # object attributes
        # ---------------------------------------------------------------------
        # string
        self.defaultRepo = "https://github.com/douglasbeniz/e3"
        self.requireVersion = ''
        self.baseVersion = ''
        # ---------------------------------------------------------------------
        # integer/float
        # ---------------------------------------------------------------------
        # boolean
        self.agrementAccepted = False
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
        self.checkAgree.stateChanged.connect(self.updateAgreementAcceptance)
        self.lstRequire.itemSelectionChanged.connect(self.updateRequireVersion)
        self.lstBase.itemSelectionChanged.connect(self.updateBaseVersion)
        # ---------------------------------------------------------------------
        # configuring envent filter for tab
        self.tabInstallSteps.tabBar().installEventFilter(self)


    @pyqtSlot(int)
    def updateSelectedTab(self, val):
        # print("New selected tab: %d" % val)
        pass

    @pyqtSlot(int)
    def updateAgreementAcceptance(self, val):
        # 
        self.agrementAccepted = self.checkAgree.isChecked()
        # print("license accepted: " + str(self.agrementAccepted))
        self.pushNext.setEnabled(self.agrementAccepted)


    @pyqtSlot()
    def updateRequireVersion(self):
        #
        try:
            self.requireVersion = self.lstRequire.selectedItems()[0].text()
        except:
            pass


    @pyqtSlot()
    def updateBaseVersion(self):
        #
        try:
            self.baseVersion = self.lstBase.selectedItems()[0].text()
        except:
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
        if step == 0:       # main
            pass
        elif step == 1:     # license
            try:
                returnedLicense = requests.get('%s//%s' % (self.defaultRepo,'raw/master/LICENSE'))
                if (returnedLicense.status_code == 200):
                    # if that was fine, show it
                    self.textLicense.setText(str(returnedLicense.content.decode('utf-8')))
                elif (returnedLicense.status_code == 404):
                    self.textLicense.setText('')
                    self.statusBar.showMessage('Error when trying to get license file...', 15000)
            except Exception as e:
                raise e
        elif step == 2:     # versions
            try:
                errMessage = None
                # -------------------------------------------------------------
                # ESS Require
                # -------------------------------------------------------------
                if (self.lstRequire.count() == 0):
                    returnedTags = requests.get(REQUIRE_ESS_REPO_API_TAGS)
                    if (returnedTags.status_code == 200):
                        tagsList = []
                        for tag in returnedTags.json():
                            tagsList.append(tag['name'])
                        self.lstRequire.addItems(tagsList)
                        # for index in range(self.lstRequire.count()):
                        #     self.lstRequire.item(index).setCheckState(Qt.Unchecked)
                        # self.lstRequire.item(0).setCheckState(Qt.Checked)
                        self.lstRequire.item(0).setSelected(True)
                        self.requireVersion = self.lstRequire.item(0).text()
                    else:
                        errMessage = 'ESS-Require'
                # -------------------------------------------------------------
                # EPICS Base
                # -------------------------------------------------------------
                if (self.lstBase.count() == 0):
                    returnedTags = requests.get(EPICS_BASE_REPO_API_TAGS)
                    if (returnedTags.status_code == 200):
                        tagsList = []
                        for tag in returnedTags.json():
                            if (str(tag['name']).startswith('R')):
                                tagsList.append(tag['name'])
                        self.lstBase.addItems(tagsList)
                        self.lstBase.item(0).setSelected(True)
                        self.baseVersion = self.lstBase.item(0).text()
                    else:
                        errMessage = ('EPICS Base' if errMessage is None else errMessage + ' and EPICS-Base')


                if (errMessage):
                    self.statusBar.showMessage("Error when trying to get %s available versions..." % errMessage, 15000)

            except Exception as e:
                raise e
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