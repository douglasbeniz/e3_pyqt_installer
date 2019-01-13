#from fbs_runtime.application_context import ApplicationContext
from PyQt5.QtWidgets import QMainWindow, QApplication, QInputDialog, QFileDialog, QLineEdit, QMessageBox
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QProcess, QThread, QEvent, Qt
from PyQt5.uic import loadUi

from enum import Enum
from pathlib import Path
#from time import QThread.sleep
from functools import partial

import sys, os
import requests
import subprocess
import shutil
import time

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

        # process correspondent step
        self.processInstallationStep(nextIndex)


    def pushLocalDirClicked(self):
        localDir = QFileDialog.getExistingDirectory(self, "EPICS installation via e3", self.defaultLocalDir, QFileDialog.ShowDirsOnly)
        if localDir:
            self.defaultLocalDir = localDir
            self.localDir = localDir + '/e3'
            self.localDir = self.localDir.replace('//', '/')
            self.textLocalDir.setText(self.localDir)


    def pushTargetDirClicked(self):
        targetDir = QFileDialog.getExistingDirectory(self, "EPICS installation via e3", self.defaultTargetDir, QFileDialog.ShowDirsOnly)
        if targetDir:
            self.defaultTargetDir = targetDir
            self.targetDir = targetDir + '/epics'
            self.targetDir = self.targetDir.replace('//', '/')
            self.textTargetDir.setText(self.targetDir)


    """
    * ---------------------------------------------------------------------------
    * Since all the parameters were set, proceeds with installation
    * ---------------------------------------------------------------------------
    """
    def pushInstallClicked(self):
        self.statusBar.showMessage('This will take a while, take a cup of tea or coffee, or go to work on something else...', 15000)
        try:
            # -----------------------------------------------------------------------
            cloneDir = ('%s/%s%s') % (self.localDir, 'e3-', self.baseVersion)
            cloneDir = cloneDir.replace('//', '/')
            if not os.path.exists(self.localDir):
                os.makedirs(self.localDir)
            if (os.path.exists(cloneDir)):
                choice = QMessageBox.question(self,
                        "EPICS installation via e3",
                        "It already exists a clone of e3 to desired EPICS version.\n\nWould you like to overwrite it on cancel the operation?",
                        QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
                if choice == QMessageBox.Yes:
                    shutil.rmtree(cloneDir)
                    #pass
                else:
                    return 1
            if not os.path.exists(self.targetDir):
                os.makedirs(self.targetDir)

            # -----------------------------------------------------------------------
            # running processes in sequence...
            # -----------------------------------------------------------------------
            # cloning the e3 repo
            self.processGitClone.start('git', ['clone', self.defaultRepo, cloneDir])
            while not self.processGitClone.waitForFinished():
                QThread.sleep(0.2)
            self.processGitClone.close()
            # -----------------------------------------------------------------------
            # configure the e3 environment settings
            configSetupParams = ['-t%s' % self.targetDir,              # target directory
                '-b%s' % self.baseVersion.replace('R',''),             # EPICS base version
                '-r%s' % self.requireVersion.replace('v',''),          # require version
                '-y',                                                   # force to accept the cnofiguration as default (yes)
                'setup']                                                # run the setup procedure
            self.processConfigSetup.setWorkingDirectory(cloneDir)
            self.processConfigSetup.start(('%s/%s') % (cloneDir,'e3_building_config.bash'), configSetupParams)
            while not self.processConfigSetup.waitForFinished():
                QThread.sleep(0.2)
            self.processConfigSetup.close()
            # -----------------------------------------------------------------------
            # EPICS base
            self.processEpicsBase.setWorkingDirectory(cloneDir)
            self.processEpicsBase.start(('%s/%s') % (cloneDir,'e3.bash'), ['base'])
            while not self.processEpicsBase.waitForFinished():
                QThread.sleep(0.2)
            self.processEpicsBase.close()
            # -----------------------------------------------------------------------
            # Require
            self.processRequire.setWorkingDirectory(cloneDir)
            self.processRequire.start(('%s/%s') % (cloneDir,'e3.bash'), ['req'])
            while not self.processRequire.waitForFinished():
                QThread.sleep(0.2)
            self.processRequire.close()
            # -----------------------------------------------------------------------
            # Module groups
            #   e.g.:
            #       ./e3.bash -cta4 mod
            #       ./e3.bash -ctao mod
            self.processModules.setWorkingDirectory(cloneDir)
            self.processModules.start(('%s/%s') % (cloneDir,'e3.bash'), [self.e3Modules, 'mod'])
            while not self.processModules.waitForFinished():
                QThread.sleep(0.2)
            self.processModules.close()
            # -----------------------------------------------------------------------
            # Check the installation
            # -----------------------------------------------------------------------
            self.statusBar.showMessage('Installation procedures concluded!', 15000)
            # saving all the log into a file
            with open(os.path.join(cloneDir, 'installation_log_%s.txt' % time.strftime('%d%h%Y-%Hh%Mm%Ss')), 'w') as logFile, \
                open(os.path.join(self.targetDir, 'installation_log_%s.txt' % time.strftime('%d%h%Y-%Hh%Mm%Ss')), 'w') as logFileTarget:
                logFile.write(self.textLog.toPlainText())
                logFile.close()
                logFileTarget.write(self.textLog.toPlainText())
                logFileTarget.close()

        except:
            self.statusBar.showMessage('An exception occurred... ask for support!', 15000)
            self.pushInstall.setEnabled(True)
            return 1

        return 0


    """
    generic
    """
    def showProcessResults(self, process):
        self.textLog.append(str(process.readAllStandardOutput(), 'utf-8'))

    def showProcessErrors(self, process):
        self.statusBar.showMessage(str(process.readAllStandardError(), 'utf-8'), 15000)


    """
    specific
    """
    def startedGitClone(self):
        # cloning the e3 repo
        self.textLog.append('---\nCloning the e3 repo...\n')
        self.pushInstall.setEnabled(False)

    def finishedGitClone(self):
        # cloning the e3 repo
        self.textLog.append('---\nCloning step has been concluded with exitCode: %d' % self.processGitClone.exitCode())

    def startedConfigSetup(self):
        # cloning the e3 repo
        self.textLog.append('---\nConfigure the e3 environment settings...\n')

    def finishedConfigSetup(self):
        # cloning the e3 repo
        self.textLog.append('---\nConfiguration step has been concluded with exitCode: %d' % self.processConfigSetup.exitCode())

    def startedEpicsBase(self):
        # cloning the e3 repo
        self.textLog.append('---\nInstall EPICS Base...\n')

    def finishedEpicsBase(self):
        # cloning the e3 repo
        self.textLog.append('---\nEPCIS base installation step has been concluded with exitCode: %d' % self.processConfigSetup.exitCode())

    def startedRequire(self):
        # cloning the e3 repo
        self.textLog.append('---\nInstall Require...\n')

    def finishedRequire(self):
        # cloning the e3 repo
        self.textLog.append('---\nRequire installation step has been concluded with exitCode: %d' % self.processConfigSetup.exitCode())
        self.pushInstall.setEnabled(True)

    def startedModules(self):
        # cloning the e3 repo
        self.textLog.append('---\nInstall Module groups...\n')

    def finishedModules(self):
        # cloning the e3 repo
        self.textLog.append('---\nModule groups installation step has been concluded with exitCode: %d' % self.processConfigSetup.exitCode())
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
        self.e3Modules          = None
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

        self.e3ModulesParamDict = {
            ModuleGroups.CMNGRP: 'c',
            ModuleGroups.TMGGRP: 't',
            ModuleGroups.EV4GRP: '4',
            ModuleGroups.ECMGRP: 'e',
            ModuleGroups.PSIGRP: 'i',
            ModuleGroups.IFCGRP: 'f',
            ModuleGroups.ADRGRP: 'a',
            ModuleGroups.LRFGRP: 'l'
        }
        # ---------------------------------------------------------------------
        # Qt types
        self.processGitClone    = QProcess(self)
        self.processConfigSetup = QProcess(self)
        self.processEpicsBase   = QProcess(self)
        self.processRequire     = QProcess(self)
        self.processModules     = QProcess(self)

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
        self.pushClearLog.clicked.connect(lambda: self.textLog.setText(''))
        self.actionRepo.triggered.connect(self.menuActionRepo)
        self.processGitClone.readyReadStandardOutput.connect(partial(self.showProcessResults, self.processGitClone))
        self.processGitClone.readyReadStandardError.connect(partial(self.showProcessErrors, self.processGitClone))
        self.processConfigSetup.readyReadStandardOutput.connect(partial(self.showProcessResults, self.processConfigSetup))
        self.processConfigSetup.readyReadStandardError.connect(partial(self.showProcessErrors, self.processConfigSetup))
        self.processEpicsBase.readyReadStandardOutput.connect(partial(self.showProcessResults, self.processEpicsBase))
        self.processEpicsBase.readyReadStandardError.connect(partial(self.showProcessErrors, self.processEpicsBase))
        self.processRequire.readyReadStandardOutput.connect(partial(self.showProcessResults, self.processRequire))
        self.processRequire.readyReadStandardError.connect(partial(self.showProcessErrors, self.processRequire))
        self.processModules.readyReadStandardOutput.connect(partial(self.showProcessResults, self.processModules))
        self.processModules.readyReadStandardError.connect(partial(self.showProcessErrors, self.processModules))
        self.processGitClone.started.connect(self.startedGitClone)
        self.processGitClone.finished.connect(self.finishedGitClone)
        self.processConfigSetup.started.connect(self.startedConfigSetup)
        self.processConfigSetup.finished.connect(self.finishedConfigSetup)
        self.processEpicsBase.started.connect(self.startedEpicsBase)
        self.processEpicsBase.finished.connect(self.finishedEpicsBase)
        self.processRequire.started.connect(self.startedRequire)
        self.processRequire.finished.connect(self.finishedRequire)
        self.processModules.started.connect(self.startedModules)
        self.processModules.finished.connect(self.finishedModules)
        # ---------------------------------------------------------------------
        # connecting slots and form components
        self.tabInstallSteps.currentChanged.connect(self.updateSelectedTab)
        self.chkAgree.stateChanged.connect(self.updateAgreementAcceptance)
        self.lstRequire.itemSelectionChanged.connect(self.updateRequireVersion)
        self.lstBase.itemSelectionChanged.connect(self.updateBaseVersion)
        self.lstModules.itemSelectionChanged.connect(self.updateSelectedModules)
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
        self.agrementAccepted = self.chkAgree.isChecked()
        self.statusBar.showMessage('License accepted: ' + str(self.agrementAccepted), 15000)
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
        self.defaultTargetDir   = '/opt'
        self.localDir           = (str(Path.home()) + '/e3').replace('//', '/')
        self.targetDir          = '/opt/epics'


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
            # filling up the attribute that will be used when running the Modules installation procedure
            self.e3Modules = '-'
            for e3Mod in moduleEnumList:
                self.e3Modules += str(self.e3ModulesParamDict[e3Mod])
            if self.chkOnly.isChecked():
                self.e3Modules += 'o'
            #print(self.e3Modules)

            self.initialDirPlaces()
            self.textLocalDir.setText(self.localDir)
            self.textTargetDir.setText(self.targetDir)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = e3InstallerWindow()
    mainWin.show()
    # wait until the window is closed...
    sys.exit(app.exec_())