#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QTranslator, QCoreApplication, QLocale
from PySide6.QtWidgets import QApplication

from resources import resource


if getattr(sys, 'frozen', False):
    APP_PATH = Path(sys.executable).parent.resolve()
else:
    APP_PATH = Path(__file__).parent.resolve()


class App(QObject):
    projectCreated = Signal(Path)
    meshUpdated = Signal()
    restarted = Signal()

    def __init__(self):
        super().__init__()

        self._window = None
        self._vtkMesh = None
        self._cellZoneActors = None
        self._translator = None
        self._plug = None

    @property
    def window(self):
        return self._window

    @property
    def renderingView(self):
        return self._window.renderingView()

    @property
    def plug(self):
        return self._plug

    def setPlug(self, plug):
        self._plug = plug

    def vtkMesh(self):
        return self._vtkMesh

    def cellZoneActor(self, czid):
        return self._cellZoneActors[czid].face

    def openMainWindow(self):
        self._window = self._plug.createMainWindow()
        self._window.show()

    def updateVtkMesh(self, mesh, cellZoneActors):
        if self._vtkMesh:
            self._vtkMesh.deactivate()

        self._vtkMesh = mesh
        self._cellZoneActors = cellZoneActors
        self._window.vtkMeshLoaded()
        self.showMesh()
        self.meshUpdated.emit()

    def showMesh(self):
        if self._vtkMesh:
            self._vtkMesh.activate()

    def hideMesh(self):
        if self._vtkMesh:
            self._vtkMesh.deactivate()

    def quit(self):
        self._window = None
        QApplication.quit()

    def restart(self):
        self.restarted.emit()

    def setLanguage(self, language):
        QCoreApplication.removeTranslator(self._translator)
        self._translator = QTranslator()
        self._translator.load(QLocale(QLocale.languageToCode(QLocale(language).language())),
                              'baram', '_', str(resource.file('locale')))
        QCoreApplication.installTranslator(self._translator)


app = App()
