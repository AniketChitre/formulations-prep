# -*- coding: utf-8 -*-
"""
Created on Sun Nov  6 21:12:21 2022

@author: SRIH01
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


class PipettingSpecies:
    def __init__(self,name,density,chemicalType):
        self.name = name
        self.density = density
        self.chemicalType = chemicalType
        
    def readCSV(filename):
        df = pd.read_csv(filename)
        speciesList = []
        for i in range(len(df)):
            newSpecies = PipettingSpecies(name=df['name'].loc[i],density=df['density'].loc[i],chemicalType=df['type'].loc[i])
            speciesList.append(newSpecies)
        return speciesList
    
    def getSpecies(specList,specName):
        for spec in specList:
            if spec.name == specName:
                return spec
            
    def getVolume(self,mass):
        return mass/self.density
    
    def getMass(self,volume):
        return volume*self.density
        
class PipettingStep:    
    def __init__(self,species,volume,sample):
        self.species = species
        self.targetVol = volume
        self.sample = sample
        
    def addToSample(self):
        self.sample.actualMass = self.sample.actualMass + self.addedMass
        self.sample.addedMassSeries[self.species.name] = self.sample.addedMassSeries[self.species.name] + self.addedMass
        
    def createSteps(instructions,speciesDictionary,sampleList,maxVol):
        stepList=[]
        for colName in instructions.columns:
            if colName == 'ID':
                sampleIds = instructions[colName]
            else:
                species = PipettingSpecies.getSpecies(speciesDictionary, colName)
                colVal = instructions[colName]               
                i = 0
                for val in colVal:
                    if val > 0.0:
                        val=val/100
                        sample = PipettingSample.getSample(sampleIds.iloc[i], sampleList)
                        volume = sample.calcVolumeFrac(species,val)*sample.targetVolume #species.getVolume(val)*sample.totalDensity*targetVolume
                        if volume>maxVol:
                            step = PipettingStep(species, volume/2, sample)
                            stepList.append(step)
                            stepList.append(step)
                        else:
                            step = PipettingStep(species, volume, sample)
                            stepList.append(step)
                    i=i+1
        return stepList
                   
class PipettingSample:
    def __init__(self,sampleId,massFracSeries,targetVolume):
        self.sampleId = sampleId
        self.massFracSeries = massFracSeries
        self.addedMassSeries = pd.Series(dtype='float64').reindex_like(self.massFracSeries)
        self.addedMassSeries.values[:]=0.0
        self.massFracWater = 1 - sum(massFracSeries)
        self.targetVolume = targetVolume
        
    def getTotalDensity(self,speciesDictionary):
        denom = 0
        num = 0
        for (specName,massFrac) in self.massFracSeries.iteritems():
            spec = PipettingSpecies.getSpecies(speciesDictionary, specName)
            denom = denom + massFrac / spec.density
            num = num + massFrac
        water = PipettingSpecies.getSpecies(speciesDictionary, 'water')
        denom = denom + self.massFracWater / water.density
        num = num + self.massFracWater
        self.totalDensity = num/denom
        
        
    def getVolFracSeries(self,speciesDictionary):
        self.volFracSeries = pd.Series(dtype='float64').reindex_like(self.massFracSeries)
        self.volFracSeries.values[:]=0.0
        for (name,val) in self.volFracSeries.iteritems():
            species = PipettingSpecies.getSpecies(speciesDictionary,name)
            self.volFracSeries[name] = self.calcVolumeFrac(species,self.massFracSeries[name]) # species.getVolume(mass=self.massFracSeries[name]) * self.totalDensity
        waterVolFrac = 1- self.volFracSeries.sum()
        self.waterVol = waterVolFrac * self.targetVolume
        
    def calcVolumeFrac(self,species,massFrac):
        return massFrac*self.totalDensity/species.density
        
    def calcMassFrac(self,species,volFrac):
        return volFrac/self.totalDensity*species.density
        
    def createSamples(instructions,targetVol):
        sampleList = []
        for i in range(len(instructions)):
            instruction = instructions.iloc[i]
            sample = PipettingSample(sampleId=instruction['ID'],massFracSeries=instruction.drop(instruction.index[0:1])/100,targetVolume=targetVol)
            sampleList.append(sample)
        return sampleList
    
        
    def getSample(id,sampleList):
        for sample in sampleList:
            if sample.sampleId == id:
                return sample
        
class PipettingInstructions:
    def readCSV(filename,firstRow=-6,lastRow=None,deleteColumns = ['Sample','Water','Sample Density']):
        instructionsFull = pd.read_csv(filename)
        instructionsFull = instructionsFull.loc[:, ~instructionsFull.columns.str.contains('^Unnamed')]
        instructions = instructionsFull.iloc[firstRow:lastRow]
        instructions = instructions.drop([x for x in deleteColumns if x in instructions.columns],axis=1)
        return instructions
        
class MassProfile:
    def __init__(self,filename,t_baseline,derivNoise=0,secDerivNoise=0):
        massProfile = pd.read_csv(filename)
        self.time = massProfile['Time']
        self.raw = massProfile['Mass']
        self.mass = massProfile['Mass']
        self.t_baseline = t_baseline
        self.derivNoise = derivNoise
        self.secDerivNoise = secDerivNoise

    
    def showProfiles(self):
        fig, ax1 = plt.subplots()

        ax2 = ax1.twinx()
        ax1.plot(self.time, self.raw, 'r-')
        ax1.plot(self.time, self.mass, 'g-')
        ax2.plot(self.time, self.dmdt, 'b-')
        ax2.plot(self.time, self.d2mdt, 'y-')
        
        ax1.set_xlabel('time [s]')
        ax1.set_ylabel('Mass [g]', color='g')
        ax2.set_ylabel('Derivative [g/s]', color='b')

        plt.show()
        
    def smoothData(self,window):
        if window==1:
            self.mass = self.raw
        else:
            self.mass=self.raw.rolling(window=window).mean()
        
    def analyseWater(self,avg_window,bl_mult):
        self.smoothData(avg_window)
        self.ddt()
        deriv_baseline=bl_mult*np.nanmax(abs(self.dmdt[0:self.t_baseline]))
        start_idx = next(x for x, val in enumerate(self.dmdt) if val>deriv_baseline) -1
        start_mass = np.median(self.mass[start_idx-2:start_idx])
        end_idx = next(x for x, val in enumerate(self.dmdt) if val<deriv_baseline and x> start_idx)
        end_mass = np.median(self.mass[end_idx:end_idx+2])
        water_mass = end_mass-start_mass
        print("Water Transfer started at t="+str(self.time[start_idx])+"s and ended at t="+str(self.time[end_idx]) + "s; mass=" + str(water_mass) + "g")
        return water_mass, end_idx
        #self.showProfiles()
        
    def analyseIngredients(self,avg_window,bl_mult,mergeSens,specType,steps,start_idx,show,thresh_mode=0):
        #thresh_mode: 0 is delta t at beginning, 1 detla t at end, 2 is absolute values
        self.smoothData(avg_window)
        self.ddt()
        self.d2dt()
        if thresh_mode==0:
            ddt_noise = np.nanmax(abs(self.dmdt[0:self.t_baseline]))
            d2dt_noise = np.nanmax(abs(self.d2mdt[0:self.t_baseline]))
        elif thresh_mode==1:
            ddt_noise = np.nanmax(abs(self.dmdt[-self.t_baseline:]))
            d2dt_noise = np.nanmax(abs(self.d2mdt[-self.t_baseline:]))
        else:
            ddt_noise = self.derivNoise
            d2dt_noise = self.secDerivNoise
        deriv_baseline=bl_mult*ddt_noise
        secderiv_baseline=bl_mult*d2dt_noise
        running_idx=start_idx
        if show:
            self.showProfiles()
        for step in steps:
            if step.species.chemicalType==specType:
                temp_idx = next(x for x, val in enumerate(self.dmdt) if abs(val)>deriv_baseline and x>running_idx)
                temp_idx2 = next(x for x, val in enumerate(self.d2mdt) if abs(val)>secderiv_baseline and x>running_idx)
                start_idx = min(temp_idx,temp_idx2) -1
                running_idx=start_idx
                criterion=False
                running_idx=max(temp_idx,temp_idx2)
                while not criterion:
                    criterion = True
                    for i in range(mergeSens-1):
                        criterion = criterion and abs(self.dmdt[running_idx+i])<deriv_baseline
                        criterion = criterion and abs(self.d2mdt[running_idx+i])<secderiv_baseline
                    else:
                        running_idx=running_idx+1
                end_idx=running_idx
                start_mass = np.median(self.mass[start_idx-2:start_idx])
                end_mass = np.median(self.mass[end_idx:end_idx+2])
                step.addedMass = end_mass-start_mass
                step.actualVol = step.sample.calcVolumeFrac(step.species,step.addedMass)
                print("Addition of " + str(round(step.addedMass,3)) + "g " + step.species.name + " detected from " + \
                      str(self.time[start_idx]) + "s to " + str(self.time[end_idx]) + "s - " + \
                          "expected volume = " + str(round(step.targetVol,3)) + "mL and actual volume = " + \
                              str(round(step.actualVol,3)) + "mL (resulting error is " + str(round(abs(1-step.actualVol/step.targetVol)*100,3)) + "%)")
                    
        return running_idx
        
        
    def ddt(self):
        self.dmdt = pd.Series(dtype='float64').reindex_like(self.mass)
        self.dmdt.values[:]=0.0
        for i in range(len(self.dmdt)):
            if i==0:
                self.dmdt[i] = (self.mass[i+1]-self.mass[i]) / (self.time[i+1]-self.time[i])
            elif i==len(self.dmdt)-1:
                self.dmdt[i] = (self.mass[i]-self.mass[i-1]) / (self.time[i]-self.time[i-1])
            else:
                self.dmdt[i] = (self.mass[i+1]-self.mass[i-1]) / (self.time[i+1]-self.time[i-1])


    def d2dt(self):
        self.d2mdt = pd.Series(dtype='float64').reindex_like(self.mass)
        self.d2mdt.values[:]=0.0
        for i in range(len(self.dmdt)):
            if i==0:
                self.d2mdt[i] = (self.dmdt[i+1]-self.dmdt[i]) / (self.time[i+1]-self.time[i])
            elif i==len(self.d2mdt)-1:
                self.d2mdt[i] = (self.dmdt[i]-self.dmdt[i-1]) / (self.time[i]-self.time[i-1])
            else:
                self.d2mdt[i] = (self.dmdt[i+1]-self.dmdt[i-1]) / (self.time[i+1]-self.time[i-1])
            

# speciesList = PipettingSpecies.readCSV('SpeciesDictionary.csv')
# instructions = PipettingInstructions.readCSV('PhD_MasterDataset_OT_Dec2022.csv')
# targetVolume = 10
# sampleList = PipettingSample.createSamples(instructions,targetVol=targetVolume)
# maxVolume = 1
# for sample in sampleList:
#     sample.getTotalDensity(speciesDictionary=speciesList)
#     sample.getVolFracSeries(speciesDictionary=speciesList)
# steps = PipettingStep.createSteps(instructions=instructions,speciesDictionary=speciesList,sampleList=sampleList,maxVol=maxVolume)

# massProfile = MassProfile('MassProfile_011222_run1.csv',t_baseline=25)

# (water_mass,t1)=massProfile.analyseWater(avg_window=10,bl_mult=3)
# water=PipettingSpecies.getSpecies(speciesList, 'water')
# water_volume_act=water.getVolume(water_mass)
# water_volume_set=0
# for sample in sampleList:
#     water_volume = sample.waterVol
#     water_volume_set = water_volume_set + water_volume
#     sample.actualMass = water_volume/water.density
# print("This equals a volume of " + str(round(water_volume_act,3)) + "m; expected was "\
#       + str(round(water_volume_set,3)) + "mL; error is " + str(round(abs((water_volume_set-water_volume_act)/water_volume_set)*100,3)) + "%")

# t2 = massProfile.analyseIngredients(avg_window=5, bl_mult=5, mergeSens=5, specType='surfactant',steps=steps,start_idx=t1,show=True)   
# t3 = massProfile.analyseIngredients(avg_window=7, bl_mult=6, mergeSens=5, specType='polyelectrolyte',steps=steps,start_idx=t2,show=True)
# t4 = massProfile.analyseIngredients(avg_window=1, bl_mult=7, mergeSens=2, specType='thickener',steps=steps,start_idx=t3,show=True)

# for step in steps:
#     step.addToSample()

# actualMassFractions = pd.DataFrame(dtype='float64').reindex_like(instructions)
# actualMassFractions[:]=0
# for i in range(len(sampleList)):
#     actualMassFractions['ID'].iloc[i] = sampleList[i].sampleId
#     for entry in sampleList[i].addedMassSeries.iteritems():
#         actualMassFractions[entry[0]].iloc[i] = entry[1]/sampleList[i].actualMass*100
# actualMassFractions.to_csv('results.csv', index=False)