#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May  7 12:48:21 2020

@author: santi
"""

import numpy as np
import warnings
import Modules.Geometria as Geometria
from Modules.Funciones import timerClass, get_hexagonal_dimensions_in_voxels


@timerClass
class Muestra(object):
  """
  la clase Muestra contiene objetos que representan el litio metálico que
  colocamos en el campo magnetico.

  Atributos
  =========
  uno de los inputs es volumen. Este proviene de la salida de la funcion
  SimulationVolume. Es un dict de tres arrays de tres elemtos. Lo desempaqueto
  asi N, voxelSize, FOV = volumen. En cada caso sigo la convencion [z,y,x]

  + N : int array x3       -  Numero de voxels en cada dimension
  + voxelSize: fl.array x3 -  Tamano de voxels en cada dimension en mm
  + FOV: fl.array x3       -  Tamano del volumen simulado en cada dimension en mm

  + matriz: np.array       -  Es la matriz de Nz*Ny*Nx que contiene el volumen
                              simulado y a la muestra. Ceros en vacio, Chi en
                              la muestra
  + chi: float             -  Susceptibilidad magnetica del material
  + geometria : string     -  Ese el nombre del constructor de la geometria.
                              Define la forma que tendra la muestra.

  + medidas : array x3     -  Tamaño, en milimetros, de la muestra, o de un
                              rectangulo que la contiene.
  + N_muestra: intarray x3 -  Numero de voxels en cada dimension de rectangulo
                              de las dimensiones self.medidas. [Nmz,Nmy,Nmx]
  + muestra : array        -  Matriz Nmz*Nmy*Nmx que contiene la muestra. Esta
                              matriz es insertada en self.matriz
  + slices : list          -  Continen los indices sobre los cuales debe
                              realizarse el slice para colocar la muestra. Es
                              una lista de tres elementos [slz,sly,slx], donde
                              cada uno de ellos es una lista con dos int
                              slj=[j_inicial, j_final+1] que indican como hacer
                              el slice en cada dimension.
  + exceptions: bool      -   defaut: True.
                              Habilita o no la detencion del codigo por las
                              excepciones en la creacion de la muestra
  + ubicacion: str        -   Metodo de cenrado de la muestra. 
                              Opciones: 
                                'centro': La muestra esta en el centro del
                                            volumen.
                                'superior': La muestra se ubica en la parte
                                            superior dejando 10 voxels de
                                            changui.
  + densidad: float       -   Densidad de area ocupada por microest. Amic/Atot
  + densidad_volumetrica: float
                          -   Densidad de volumen ocupado por microest.
                              VolMicroest/VolumenCaja                              
  + **geokwargs:          -   Argumentos que neceseita cada geometria en
                              particular
  """

  # defino el chi por defecto
  chi_Li = 24.1*1e-6 #(ppm) Susceptibilidad volumetrica
  
  
  def __init__(self, volumen, medidas=None, geometria='bulk', chi=chi_Li,
               skdp=14e-3, exceptions=True, ubicacion='centro', 
               calcular_densidad = True, **geokwargs):
    # Dadas las variables de entrada, hago algunos pasos para crear la muestra
    # y el volumen simulado:
    # 1)OBTENCION DE INPUTS E INICIALIZACION
    #   Desempaqueto las varibles N, voxelSize y FOV que vienen en el input:
    #   volumen. Con esto puedo crear el volumen de simulacion, es decir
    #   la matriz. Los atributos que seran creados mas tardes son inicializados
    #   como None
    # 2)CREACION DE LA MUESTRA
    #   2.1)
    #   Chequeo si las medidas de la muestra cumplen la condicion de no ocupar
    #   mas de la mitad del volumen y creo el atributo medidas.
    #   2.2)
    #   Determino el volumen real que tendra la muestra. Dadas las medidas de
    #   de input y el voxelSize, determino cuantos voxels necesito en cada
    #   dimension. Las medidas reales seran entonces N_muestra*voxelSize.
    #   Hago esto para crear la muestra en una matriz de menor tamaño que el
    #   volumen total.
    #   2.3)
    #   Construccion de la muestra. Llamo al constructor correspondiente usando
    #   su nombre, que viene con input geometria. Lo que me devuelve el
    #   constructor de geometria es una lista de indices en los cuales el
    #   constructor de muestra debera colocar los valores de chi, devolviendo
    #   un array con de tamaño N_muestra_z*N_muestra_y*N_muestra_x.
    #   2.4)
    #   Defino en que indices de la matriz grande va ubicada la submatriz
    #   muestra. La mustra estara ubicada en el centro del FOV.
    # 3)CREACION DEL VOLUMEN DE SIMULACION
    #   Creo el array que define el volumen de simulacion. Lueg inserto en el
    #   el centro el array de la muestra

    # 1)_______________________________________________________________________
    N, voxelSize, FOV = volumen
    N = N.astype(int)
    self.N = N
    self.voxelSize = voxelSize
    self.FOV = FOV
    self.matriz = None
    self.chi = chi
    self.geometria = geometria
    self.medidas = medidas
    self.N_muestra = None
    self.muestra = None
    self.slices = None
    self.pCubierto = None
    self.exceptions = exceptions
    self.ubicacion = ubicacion
    self.densidad = None
    self.densidad_volumetrica = None
    # 2)_______________________________________________________________________
    # 2.1) MEDIDAS: dimensiones de la muestra en mm ---------------------------
    #chequeo que el FOV tenga un tamaño adecuado
    if any(np.array(FOV) < 2*np.array(medidas)):
      mensaje= "\n ============WARNING===============\
               \n La muestra excede el 50% del FOV\
               \n =================================="
      warnings.warn(mensaje, DeprecationWarning, stacklevel=2)

    # chequeo que haya como minimo 3 veces skindepth por debajo de las
    # microestructuras    
    # min_bulk = skdp*3 # skin depth en milimetros del Li a una frecuencia de 116.6MHz
    # min_FOV = medidas[0] + 2*min_bulk # como la muestra se ubica al centro, lo que sobra arriba y abajo es lo mismo. Por eso va 2 veces min_bulk    
    # if(self.exceptions):
    #   if  FOV[0] < min_FOV :
    #     msg = "No hay suficiente FOVz para el bulk. La muestra se correra "\
    #           "hacia arriba y no estara centrada"
    #     # raise Exception(msg)
    #     warnings.warn(mensaje, DeprecationWarning, stacklevel=2)



    # 2.2)---------------------------------------------------------------------
    # Si la geometria tiene arrego hexagonal, las dimensiones deben ser reescritas:    
    if 'hexagonal' in self.geometria.lower():
      self.overwrite_medidas_with_hexagonal_parameters(geokwargs)
    elif self.medidas is None:
      self.medidas = N
    # con este metodo seteo las dimensiones de la submatriz que contiene a la
    # muestra.
    self.set_medidas()
    # 2.3)---------------------------------------------------------------------
    # obtengo los indices de los voxels "vivos"
    indices = self.construir_geometria(**geokwargs)
    # creacion de self.muestra
    self.construir_muestra(indices)
    # 2.4)---------------------------------------------------------------------
    # definicion de los slices donde se debe colocar la muestra
    self.definir_slices()
    # 3)_______________________________________________________________________
    self.construir_volumen()
    # 4)_______________________________________________________________________
    if calcular_densidad:
        self.Calcular_densidad()


  #============================================================================
  #===============================METHODS======================================
  #============================================================================
  def overwrite_medidas_with_hexagonal_parameters(self, geokwargs):
    try:
      distancia = geokwargs['distancia']
    except:
      msg = "Hexagonal-like geometry must have a\
            geokwarg called 'distancia'"
      raise Exception(msg)
    vsz, vsy, vsx = self.voxelSize
    _, Ny, Nx = self.N
    # Hexagonal arrangement unit cell is a Right Rectangle
    # with hypotenuse d and a the opposite leg of the
    # 60 deg angle.
    d = int(distancia//vsx)    
    a = get_hexagonal_dimensions_in_voxels(d)
    ## the geometry occupies half of the x-y simulated volume
    N_celdas_x = (Nx/2)//d   # // es division entera en python3  (floor)
    N_celdas_y = (Ny/2)//(2*a)
    # overwrite self.medidas    
    self.medidas[1] = N_celdas_y*(2*a)*vsy
    self.medidas[2] = N_celdas_x*d*vsx
    print(f"size of sample overwriten: {self.medidas} (mm)")

  
  
  def set_medidas(self):
    """
    seteo la cantidad de voxels que contienten a la muestra
    """
    # puedo hacer la division porque medidas y voxelSize son np.arrays
    N_muestra = self.medidas/self.voxelSize
    N_muestra = N_muestra.astype(int)
    # sobreescribo las medidas de la muestra, con las medidas correctas
    self.medidas = N_muestra*self.voxelSize
    self.N_muestra = N_muestra
    return 0
  #____________________________________________________________________________
  def construir_geometria(self, **geokwargs):
    """
    Este metodo es para crear la lista de indices que contienen el material.
    Son indices flattened, es decir, en lugar de ser tuplas (z,y,x) son un
    numero entre 0 y (Nmz*Nmy*Nmx)-1
    """
    #<<<< aca llamo al constytructor de geometria, que me devuelve lista de
    # tuplas >>>>
    # en Geometria.py estan todas las funciones para crear geometrias
    # construir es una funcion.
    constructor = Geometria.funciones(self.geometria)
    _ = constructor(self.N_muestra, self.voxelSize,**geokwargs)
    try:
    # esto es para las que me devuelven el p_cubierto
      tuplas, self.pCubierto = _
    except:
      tuplas = _

    if tuplas is None:
      indices = tuplas
    else:
      # convierto a array para que ravel lo acepte. La transpues es para que sea
      # un arrat Nindices*3 (3 columnas correspondientes a z,y,x)
      indices = np.array(tuplas).T
      # convierto a indices planos
      indices = np.ravel_multi_index(indices, self.N_muestra)
    return indices
  #____________________________________________________________________________
  def construir_muestra(self, indices):
    """
    Dados los indices, crea una matriz de N_muestra_z*N_muestra_y*N_muestra_x,
    con el valor de chi en los voxels en los que hay material
    """
    Nmz, Nmy, Nmx = self.N_muestra
    muestra_flat = np.zeros(Nmz*Nmy*Nmx)
    if indices is not None:      
      # el constructor me da una lista de indices flattened
      #  put(array       , indices, valor)
      np.put(muestra_flat, indices, self.chi)
    # convierto en 3d array
    muestra = np.reshape(muestra_flat, (Nmz,Nmy,Nmx))
    self.muestra = muestra
    return 0
  #____________________________________________________________________________
  def definir_slices(self):
    """
    Este metodo es para definir donde se debe colocar el subarray muestra, en
    el array matriz, es decir, donde coloco la muestra dentro del volumen
    """
    Nz, Ny, Nx = self.N
    Nmz, Nmy, Nmx = self.N_muestra
    # hago un slice sobre la matriz en el cual coloco la muestra. Defino indices
    # slj: slice en j, [j_inicial, j_final+1]    
    slx = [int(Nx/2-Nmx/2), int(Nx/2+Nmx/2)]
    sly = [int(Ny/2-Nmy/2), int(Ny/2+Nmy/2)]
    if 'sup' in self.ubicacion.lower(): # "superior"
        # z0 = Nz - Nmz - Nvx_seguridad        
        z0 = int(Nz - Nmz - 10)
        slz = [z0, Nz-10]
    else: # (centro:)
        slz = [int(Nz/2-Nmz/2), int(Nz/2+Nmz/2)]
    
        
    
    # para unas pruebas el dia 08/02/2022:
    # shift = 10
    # slz = [int(Nz/2-Nmz/2)+shift, int(Nz/2+Nmz/2)+shift]
      
    self.slices = [slz,sly,slx]
    return 0

  #____________________________________________________________________________
  def construir_volumen(self):
    """
    Este metodo es para crear la matriz y rellenarla con la muestra
    """
    matriz = np.zeros(self.N)
    # hago un slice sobre la matriz en el cual coloco la muestra. Defino indices
    # slj: slice en j, [j_inicial, j_final+1]
    slz, sly, slx = self.slices

    # reemplazo los valores de la muestra en la matriz de ceros:
    matriz[slz[0]:slz[1], sly[0]:sly[1], slx[0]:slx[1]] = self.muestra

    # guardo la variable matriz en el atributo matriz
    #self.matriz = matriz
    return matriz
  #____________________________________________________________________________  
  def Calcular_densidad(self):
    """
    El nombre lo dice
    """
    Nmz, Nmy, Nmx = self.N_muestra
    self.densidad  = np.sum(self.muestra[0,:,:])/self.chi / (Nmx*Nmy)
    self.densidad_volumetrica = np.sum(self.muestra)/self.chi / (Nmx*Nmy*Nmz)     
  #____________________________________________________________________________
  #____________________________________________________________________________




