#from fbs_runtime.application_context import ApplicationContext
from PyQt5.QtWidgets import QMainWindow, QApplication, QInputDialog, QFileDialog, QLineEdit, QMessageBox
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QProcess, QEvent, Qt
from PyQt5.uic import loadUi

from enum import Enum
from pathlib import Path
from time import sleep

import sys, os
import requests
import subprocess

REQUIRE_ESS_REPO            = 'https://github.com/icshwi/require-ess/releases'
REQUIRE_ESS_REPO_API_TAGS   = 'https://api.github.com/repos/icshwi/require-ess/tags'
EPICS_BASE_REPO_API_TAGS    = 'https://api.github.com/repos/epics-base/epics-base/tags'


"""
Enumerator to handle module group types
"""
class ModuleGroups(Enum):
    CMNGRP = 0,
    TMGGRP = 1,
    EV4GRP = 2,
    ECMGRP = 3,
    PSIGRP = 4,
    IFCGRP = 5,
    ADRGRP = 6,
    LRFGRP = 7


class e3InstallerWindow(QMainWindow):
    pushPreviousClicked     = pyqtSignal()
    pushNextClicked         = pyqtSignal()
    pushQuitClicked         = pyqtSignal()
    pushLocalDirClicked     = pyqtSignal()
    pushTargetDirClicked    = pyqtSignal()
    pushInstallClicked      = pyqtSignal()

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

        enableNextButton = False
        # Controls visibility
        if nextIndex == 1:                    # next tab is the license one
            enableNextButton = self.agrementAccepted
        elif nextIndex == 2:                    # next tab is the versions one
            enableNextButton = self.requireVersion is not None and self.baseVersion is not None
        elif nextIndex == 3:                    # next tab is the modules one
            enableNextButton = len(list(self.lstModules.selectedItems())) > 0
        elif nextIndex+1 == maxTabs:            # next tab is the last one
            enableNextbutton = False
        self.pushNext.setEnabled(enableNextButton)

        if nextIndex > 0:
            self.pushPrevious.setEnabled(True)

        # if nextIndex == 3:
        #     print(self.requireVersion)
        #     print(self.baseVersion)

        # process correspondent step
        self.processInstallationStep(nextIndex)


    def pushLocalDirClicked(self):
        localDir = QFileDialog.getExistingDirectory(self, "EPICS installation via e3", self.defaultLocalDir, QFileDialog.ShowDirsOnly)
        if localDir:
            self.defaultLocalDir = localDir
            self.localDir = localDir + '/e3/'
            self.targetDir = self.targetDir.replace('//', '/')
            self.textLocalDir.setText(self.localDir)


    def pushTargetDirClicked(self):
        targetDir = QFileDialog.getExistingDirectory(self, "EPICS installation via e3", self.defaultTargetDir, QFileDialog.ShowDirsOnly)
        if targetDir:
            self.defaultTargetDir = targetDir
            self.targetDir = targetDir + '/epics/'
            self.targetDir = self.targetDir.replace('//', '/')
            self.textTargetDir.setText(self.targetDir)


    """
    * ---------------------------------------------------------------------------
    * Since all the parameters were set, proceeds with installation
    * ---------------------------------------------------------------------------
    """
    def pushInstallClicked(self):
        # self.textLog.append("Local directory: " + self.localDir)
        # self.textLog.append("Target directory: " + self.targetDir)
        # -----------------------------------------------------------------------
        cloneDir = ('%s/%s%s') % (self.localDir, 'e3-', self.baseVersion)
        # cloning the e3 repo
        self.textLog.append('---\nCloning the e3 repo...\n')
        if not os.path.exists(self.localDir):
            os.makedirs(self.localDir)
        self.process.start('git', ['clone', self.defaultRepo, cloneDir])
        # -----------------------------------------------------------------------
        # configure the e3 environment settings
        self.textLog.append('---\nConfigure the e3 environment settings...\n')
        if not os.path.exists(self.targetDir):
            os.makedirs(self.targetDir)
        self.process.start(('%s/%s') % (cloneDir,'e3_building_config.bash'), ['-b %s' % self.baseVersion.replace('R',''), '-t %s' % self.targetDir, 'setup'])


    def showProcessResults(self):
        self.textLog.append(str(self.process.readAll(), 'utf-8'))


    def disableInstallButton(self):
        self.pushInstall.setEnabled(False)


    def processFinished(self, exitCode, exitStatus):
        self.textLog.append('\nThis step has been concluded with exitCode: %d\n---' % exitCode)
        self.pushInstall.setEnabled(True)


    def menuActionRepo(self):
        newRepo, confirmed = QInputDialog.getText(self, "EPICS installation via e3", "Enter the new repository URL to look at:", QLineEdit.Normal, self.defaultRepo)

        if (confirmed and newRepo and newRepo != self.defaultRepo):
            self.defaultRepo = str(newRepo)
            # Clear license file
            self.textLicense.setText('')
            # Reset license acceptance
            self.agrementAccepted = False
            self.chkAgree.setCheckState(Qt.Unchecked)
            # Clear list of versions
            self.lstBase.clear()
            self.lstRequire.clear()
            self.baseVersion = None
            self.requireVersion = None
            # Clear selected modules
            self.lstModules.clearSelection()
            self.chkOnly.setCheckState(Qt.Unchecked)
            # Clear log history and configured directories
            self.textLog.setText('')
            self.initialDirPlaces()
            # force the user to re-start the process
            self.pushPreviousClicked(reset=True)


    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)

        # ---------------------------------------------------------------------
        # object attributes
        # ---------------------------------------------------------------------
        # string
        self.defaultRepo        = 'https://github.com/douglasbeniz/e3'
        self.requireVersion     = None
        self.baseVersion        = None
        self.defaultLocalDir    = None
        self.defaultTargetDir   = None
        self.localDir           = None
        self.targetDir          = None
        # ---------------------------------------------------------------------
        # integer/float
        pass
        # ---------------------------------------------------------------------
        # boolean
        self.agrementAccepted = False
        # ---------------------------------------------------------------------
        # dictionaries
        self.modulesDict = {
            'Common Group':             ModuleGroups.CMNGRP,
            'Timing Group':             ModuleGroups.TMGGRP,
            'EPICS v4 Group':           ModuleGroups.EV4GRP,
            'EtherCAT / Motion Group':  ModuleGroups.ECMGRP,
            'PSI Module Group':         ModuleGroups.PSIGRP,
            'IFC Module Group':         ModuleGroups.IFCGRP,
            'Area Detector Group':      ModuleGroups.ADRGRP,
            'LLRF Group':               ModuleGroups.LRFGRP }
        # ---------------------------------------------------------------------
        # Qt types
        self.process = QProcess(self)

        # ---------------------------------------------------------------------
        # loading the main form
        # ---------------------------------------------------------------------
        loadUi(os.path.dirname(__file__) + '/../forms/main.ui', self)

        # ---------------------------------------------------------------------
        # from components to commands bindings
        # ---------------------------------------------------------------------
        # connecting signals and form components
        self.pushPrevious.clicked.connect(self.pushPreviousClicked)
        self.pushNext.clicked.connect(self.pushNextClicked)
        self.pushQuit.clicked.connect(self.close)
        self.pushLocalDir.clicked.connect(self.pushLocalDirClicked)
        self.pushTargetDir.clicked.connect(self.pushTargetDirClicked)
        self.pushInstall.clicked.connect(self.pushInstallClicked)
        self.actionRepo.triggered.connect(self.menuActionRepo)
        #--
        self.process.readyReadStandardOutput.connect(self.showProcessResults)
        #self.process.readyRead.connect(self.showProcessResults)
       # Disable the install button when process starts, and enable it when it finishes
        self.process.started.connect(lambda: self.pushInstall.setEnabled(False))
        self.process.finished.connect(self.processFinished)
        # ---------------------------------------------------------------------
        # connecting slots and form components
        self.tabInstallSteps.currentChanged.connect(self.updateSelectedTab)
        self.chkAgree.stateChanged.connect(self.updateAgreementAcceptance)
        self.lstRequire.itemSelectionChanged.connect(self.updateRequireVersion)
        self.lstBase.itemSelectionChanged.connect(self.updateBaseVersion)
        self.lstModules.itemSelectionChanged.connect(self.updateSelectedModules)
        # ---------------------------------------------------------------------
        # configuring envent filter for tab
        #self.tabInstallSteps.tabBar().installEventFilter(self)


    @pyqtSlot(int)
    def updateSelectedTab(self, val):
        # print("New selected tab: %d" % val)
        pass

    @pyqtSlot(int)
    def updateAgreementAcceptance(self, val):
        # 
        self.agrementAccepted = self.chkAgree.isChecked()
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


    @pyqtSlot()
    def updateSelectedModules(self):
        #
        try:
            curTab      = self.tabInstallSteps.currentIndex()+1
            maxTabs     = self.tabInstallSteps.count()
            selectCount = len(list(self.lstModules.selectedItems()))
            self.pushNext.setEnabled((selectCount > 0) and (curTab != maxTabs))
        except:
           pass



    def initialDirPlaces(self):
        self.defaultLocalDir    = str(Path.home())
        self.defaultTargetDir   = '/opt/'
        self.localDir           = str(Path.home()) + '/e3/'
        self.targetDir          = '/opt/epics/'


    def eventFilter(self, object, event): 
        if object == self.tabInstallSteps.tabBar() and \
            ((event.type() in [QEvent.KeyPress, QEvent.KeyRelease] and event.key() in [Qt.LeftArrow, Qt.RightArrow, Qt.Key_Left, Qt.Key_Right, Qt.Key_Direction_L, Qt.Key_Direction_R]) or \
             (event.type() in [QEvent.MouseButtonPress, QEvent.MouseButtonRelease] and event.button() == Qt.LeftButton)):
            # Prevent user to navigate between tabs using mouse and keyboard...
            event.ignore()
            return True
        else:
            return super(e3InstallerWindow, self).eventFilter(object, event)


    """
    * ---------------------------------------------------------------------------
    * Main procedures to perform operations of each installation stepa
    * ---------------------------------------------------------------------------
    """
    def processInstallationStep(self, step):
        if step == 0:       # main
            pass
        elif step == 1:     # license
            try:
                if (not self.textLicense.toPlainText()):
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
                # Update availabity of next push button
                self.pushNext.setEnabled(self.requireVersion is not None and self.baseVersion is not None)

                if (errMessage):
                    self.statusBar.showMessage("Error when trying to get %s available versions..." % errMessage, 15000)

            except Exception as e:
                raise e
        elif step == 3:     # modules
            # filling the modules list
            if (len(list(self.lstModules.selectedItems())) == 0):
                self.lstModules.clear()
                self.lstModules.addItems(list(self.modulesDict))
        elif step == 4:     # target
            moduleEnumList = []
            for module in list(self.lstModules.selectedItems()):
                moduleEnumList.append(self.modulesDict[module.text()])
            if (ModuleGroups.CMNGRP not in moduleEnumList):
                # need to warn user that COMMON modules are necessary to compile other modules
                choice = QMessageBox.question(self,
                    "EPICS installation via e3",
                    "Common modules group was not selected and is necessary for many others.\n\nPlease, consider to included it if this is a new installation.\n\nWould you like to add it?",
                    QMessageBox.Yes | QMessageBox.No)
                if choice == QMessageBox.Yes:
                    moduleEnumList.append(ModuleGroups.CMNGRP)
                    # select the module at the list
                    try:
                        displayedCommonName = list(self.modulesDict.keys())[list(self.modulesDict.values()).index(ModuleGroups.CMNGRP)]
                        allModulesList = [str(self.lstModules.item(idx).text()) for idx in range(self.lstModules.count())]
                        self.lstModules.item(allModulesList.index(displayedCommonName)).setSelected(True)
                    except:
                        self.statusBar.showMessage("Error when trying to set common group at modules list...", 15000)
            #print(moduleEnumList)

            self.initialDirPlaces()

            self.textLocalDir.setText(self.localDir)
            self.textTargetDir.setText(self.targetDir)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    #win = uic.loadUi(os.path.dirname(__file__) + '/../forms/main.ui')
    #win.show()
    mainWin = e3InstallerWindow()
    mainWin.show()
    # wait until the window is closed...
    sys.exit(app.exec_())