#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil
import asyncio

from coredb.project import Project


class FileLoadingError(Exception):
    pass


class FileSystem:
    TEMP_DIRECTORY_NAME = 'temp'
    CASE_DIRECTORY_NAME = 'case'
    CONSTANT_DIRECTORY_NAME = 'constant'
    BOUNDARY_CONDITIONS_DIRECTORY_NAME = '0'
    SYSTEM_DIRECTORY_NAME = 'system'
    POLY_MESH_DIRECTORY_NAME = 'polyMesh'
    BOUNDARY_DATA_DIRECTORY_NAME = 'boundaryData'
    REGION_PROPERTIES_FILE_NAME = 'regionProperties'
    FOAM_FILE_NAME = 'baram.foam'

    _casePath = None
    _constantPath = None
    _boundaryConditionsPath = None
    _systemPath = None

    @classmethod
    def setupNewCase(cls):
        cls._setCaseRoot(Project.instance().path / cls.TEMP_DIRECTORY_NAME)
        if cls._casePath.exists():
            shutil.rmtree(cls._casePath)

        cls._casePath.mkdir(exist_ok=True)
        with open(cls.foamFilePath(), 'a'):
            pass

        cls._boundaryConditionsPath = cls.makeDir(cls._casePath, cls.BOUNDARY_CONDITIONS_DIRECTORY_NAME)
        cls._systemPath = cls.makeDir(cls._casePath, cls.SYSTEM_DIRECTORY_NAME)

    @classmethod
    def setupForProject(cls):
        cls._setCaseRoot(Project.instance().path / cls.CASE_DIRECTORY_NAME)

    @classmethod
    def initRegionDirs(cls, rname):
        cls.makeDir(cls._boundaryConditionsPath, rname)
        cls.makeDir(cls._constantPath, rname)
        cls.makeDir(cls._systemPath, rname)

    @classmethod
    def caseRoot(cls):
        return cls._casePath

    @classmethod
    def constantPath(cls, rname=None):
        return cls._constantPath / rname if rname else cls._constantPath

    @classmethod
    def boundaryConditionsPath(cls, rname=None):
        return cls._boundaryConditionsPath / rname if rname else cls._boundaryConditionsPath

    @classmethod
    def systemPath(cls, rname=None):
        return cls._systemPath / rname if rname else cls._systemPath

    @classmethod
    def boundaryFilePath(cls, rname):
        return cls.constantPath(rname) / cls.POLY_MESH_DIRECTORY_NAME / 'boundary'

    @classmethod
    def cellZonesFilePath(cls, rname):
        return cls.constantPath(rname) / cls.POLY_MESH_DIRECTORY_NAME / 'cellZones'

    @classmethod
    def boundaryDataPath(cls, rname):
        return cls.constantPath(rname) / rname / cls.BOUNDARY_DATA_DIRECTORY_NAME

    @classmethod
    def foamFilePath(cls):
        return cls._casePath / cls.FOAM_FILE_NAME

    @classmethod
    def makeDir(cls, parent, directory):
        path = parent / directory
        path.mkdir(exist_ok=True)
        return path

    @classmethod
    def isPolyMesh(cls, path):
        return all([path.joinpath(f).is_file() for f in ['boundary', 'faces', 'neighbour', 'owner', 'points']])

    @classmethod
    def _copyMeshFromInternal(cls, directory, regions):
        if cls._constantPath.exists():
            shutil.rmtree(cls._constantPath)
        cls._constantPath.mkdir(exist_ok=True)

        srcFile = directory / cls.REGION_PROPERTIES_FILE_NAME
        if srcFile.is_file():
            objFile = cls.constantPath(cls.REGION_PROPERTIES_FILE_NAME)
            shutil.copyfile(srcFile, objFile)

            for rname in regions:
                srcPath = directory / rname / cls.POLY_MESH_DIRECTORY_NAME
                objPath = cls.constantPath(rname) / cls.POLY_MESH_DIRECTORY_NAME
                shutil.copytree(srcPath, objPath, copy_function=shutil.copyfile)
        else:
            polyMeshPath = cls.constantPath(cls.POLY_MESH_DIRECTORY_NAME)
            shutil.copytree(directory, polyMeshPath, copy_function=shutil.copyfile)

    @classmethod
    async def copyMeshFrom(cls, directory, regions):
        await asyncio.to_thread(cls._copyMeshFromInternal, directory, regions)

    @classmethod
    async def copyFileToCase(cls, file):
        await asyncio.to_thread(shutil.copyfile, file, cls._casePath / file.name)

    @classmethod
    async def removeFile(cls, file):
        path = cls._casePath / file
        path.unlink()

    @classmethod
    def save(cls):
        targetPath = Project.instance().path / cls.CASE_DIRECTORY_NAME
        if cls._casePath != targetPath:
            if targetPath.exists():
                shutil.rmtree(targetPath)
            cls._casePath.rename(targetPath)
            cls._setCaseRoot(targetPath)

    @classmethod
    def saveAs(cls, projectPath):
        targetPath = projectPath / cls.CASE_DIRECTORY_NAME
        shutil.copytree(cls._casePath, targetPath, dirs_exist_ok=True)

    @classmethod
    def initialize(cls, regions):
        latestTimeDir = cls._casePath / '-1'
        keepFiles = [cls.CONSTANT_DIRECTORY_NAME, cls.SYSTEM_DIRECTORY_NAME, cls.FOAM_FILE_NAME]
        for file in cls._casePath.glob('*'):
            if file.is_dir and file.name.isnumeric():
                if float(file.name) > float(latestTimeDir.name):
                    shutil.rmtree(latestTimeDir, ignore_errors=True)
                    latestTimeDir = file
                else:
                    shutil.rmtree(file)
            elif file.name not in keepFiles:
                cls._remove(file)
        latestTimeDir.rename(cls._boundaryConditionsPath)

        if len(regions) == 1 and not regions[0]:
            cls._clearDirectory(cls._constantPath, [cls.POLY_MESH_DIRECTORY_NAME])
        else:
            for file in cls._constantPath.glob('*'):
                if file.name in regions:
                    cls._clearDirectory(file, [cls.POLY_MESH_DIRECTORY_NAME])
                elif file.name != cls.REGION_PROPERTIES_FILE_NAME:
                    cls._remove(file)

        cls._clearDirectory(cls._systemPath, ['controlDict'])

    @classmethod
    def _setCaseRoot(cls, path):
        cls._casePath = path
        cls._constantPath = cls._casePath / cls.CONSTANT_DIRECTORY_NAME
        cls._boundaryConditionsPath = cls._casePath / cls.BOUNDARY_CONDITIONS_DIRECTORY_NAME
        cls._systemPath = cls._casePath / cls.SYSTEM_DIRECTORY_NAME

    @classmethod
    def _clearDirectory(cls, directory, filesToKeep):
        for file in directory.glob('*'):
            if file.name not in filesToKeep:
                cls._remove(file)

    @classmethod
    def _remove(cls, file):
        if file.is_dir():
            shutil.rmtree(file)
        else:
            file.unlink()
