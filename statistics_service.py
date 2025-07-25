# -*- coding: utf-8 -*-
"""
/***************************************************************************
 StatisticsService
                                 A QGIS plugin
 Lallemand Plant Care
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2023-09-28
        git sha              : $Format:%H$
        copyright            : (C) 2023 by ETG
        email                : etg@email.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import numpy as np
import pandas as pd
from scipy.stats import f_oneway

from .layer_service import LayerService
from .message_service import MessageService
from ..constants import GAIN_SURFACE_DATA, STATISTICS_INTERVAL
from ...gui.settings.options_settings_dlg import OptionsSettingsPage


class StatisticsService:

    def __init__(self):
        self.settings = OptionsSettingsPage()
        self.krigingSettings = self.settings.getKrigingSettings()
        self.surfaceGainData = GAIN_SURFACE_DATA
        self.statisticsInterval = STATISTICS_INTERVAL
        self.layerService = LayerService()
        self.messageService = MessageService()

    @staticmethod
    def layerToDataFrame(layer, field):
        listOfValues = [feature[field] for feature in layer.getFeatures()]
        return pd.DataFrame({field: listOfValues})

    def calculateAnovaTest(self, field, firstLayer, secondLayer):
        firstDataFrame = self.layerToDataFrame(firstLayer, field)
        secondDataFrame = self.layerToDataFrame(secondLayer, field)
        fValue, pValue = f_oneway(firstDataFrame, secondDataFrame)
        return fValue.item(), pValue.item()

    def calculateMean(self, layer, field):
        dataFrame = self.layerToDataFrame(layer, field)
        return dataFrame.mean().item()

    def calculateStdDev(self, layer, field):
        dataFrame = self.layerToDataFrame(layer, field)
        return dataFrame.std().item()

    def calculateMode(self, layer, field):
        dataFrame = self.layerToDataFrame(layer, field)
        modeResult = dataFrame[field].mode()

        if not modeResult.empty:
            return modeResult.iloc[0]
        else:
            return None

    def calculateSum(self, layer, field):
        dataFrame = self.layerToDataFrame(layer, field)
        return dataFrame.sum().item()

    def calculateMedian(self, layer, field):
        dataFrame = self.layerToDataFrame(layer, field)
        return dataFrame.median().item()

    def getGainStatistics(self, layer, field):
        return [self.calculateSum(layer, field),
                self.calculateMean(layer, field),
                self.calculateMode(layer, field),
                self.calculateMedian(layer, field),
                self.calculateStdDev(layer, field)]

    def getAnovaStatistics(self, field, firstLayer, secondLayer):
        mean = [self.calculateMean(firstLayer, field),
                self.calculateMean(secondLayer, field)]
        stdDev = [self.calculateStdDev(firstLayer, field),
                  self.calculateStdDev(secondLayer, field)]
        return mean, stdDev

    @staticmethod
    def calculateVectorClasses(layer):
        numberClasses = 4
        minValue = 0 if layer.minimumValue(layer.fields().indexOf('yield')) < 0 else layer.minimumValue(
            layer.fields().indexOf('yield'))
        maxValue = layer.maximumValue(layer.fields().indexOf('yield'))
        step = (maxValue - minValue) / numberClasses
        classes = list()
        for i in range(numberClasses + 1):
            classes.append(int(round(minValue + i * step, 0)))

        return classes

    def runStatistics(self, layer):
        intervals = self.calculateVectorClasses(layer)
        valuesList = [feature['yield'] for feature in layer.getFeatures()]

        area = float(self.krigingSettings[1][0]) * float(self.krigingSettings[1][1])
        sq_area = [area for value in valuesList]
        df = pd.DataFrame({'yield': valuesList, 'area': sq_area})

        conditions = [
            df['yield'] < intervals[0],
            (df['yield'] >= intervals[0]) & (df['yield'] < intervals[1]),
            (df['yield'] >= intervals[1]) & (df['yield'] < intervals[2]),
            df['yield'] >= intervals[2]
        ]
        choices = [f'< {intervals[0]}', f'{intervals[0]} - {intervals[1]}', f'{intervals[1]} - {intervals[2]}', f'> {intervals[2]}']
        df['interval'] = np.select(conditions, choices, default='other')

        self.surfaceGainData['TOTAL_AREA'] = df['area'].sum()
        self.surfaceGainData['TOTAL_YIELD_PRODUCTION'] = df['yield'].sum()

        results = {}
        for choice in choices:

            interval_df = df[df['interval'] == choice]
            sq_area_sum = interval_df['area'].sum()
            perc_area = (sq_area_sum / self.surfaceGainData['TOTAL_AREA']) * 100
            yield_sum = interval_df['yield'].sum()
            yield_by_perc_area = yield_sum / perc_area if perc_area != 0 else 0

            results[choice] = {
                'Area Percent': round(perc_area, 2),
                'Yield per Area Percent': round(yield_by_perc_area, 2)
            }

        return self.formatStatistics(results)

    def formatStatistics(self, stats):
        intervals = []
        area_percents = []
        yields = []

        for key, value in stats.items():
            intervals.append(key)
            area_percents.append(f"{value['Area Percent']:.3f}%")
            yields.append(f"{value['Yield per Area Percent']:.3f}")

        formatted_result = {
            'interval_strings': '\n'.join(intervals),
            'interval_area_percentage': '\n'.join(area_percents),
            'interval_total': '\n'.join(yields)
        }

        return formatted_result
