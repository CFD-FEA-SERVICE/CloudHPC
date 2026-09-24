#!/usr/bin/env python

###
### This file is generated automatically by SALOME v9.4.0 with dump python functionality
###

def tenuFemPreprocessing(text):

    import sys
    import salome

    import numpy
    import os
    from xml.dom import minidom   #for xml parsing

    #import GUI load file
    #import tkinter as tk
    #from tkinter import filedialog

    from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit, QFileDialog
    from PyQt5.QtGui import QIcon

    salome.salome_init()
    import salome_notebook
    notebook = salome_notebook.NoteBook()

    #root = tk.Tk()
    #root.withdraw()

    ##################################################
    ## 1    LOAD VARIABLES
    ##################################################

    #open the xml input file

    path, _ = QFileDialog.getOpenFileName(None,"QFileDialog.getOpenFileName()", "","All Files (*);;XML Files (*.xml)",)
    #path = filedialog.askopenfilename()

    #trim the xml filename to have a working path
    work_path = os.path.dirname(path)

    print('-- WORKING DIRECTORY :')
    print(str(work_path))


    #import the xml
    mydoc = minidom.parse( work_path + '/FEM_input.xml')

    #---IMPORT CHECK---------------------------
    if mydoc is None:
      print("NO XML FILE FOUND - ERROR ") 
    #------------------------------------------


    #define XML import list of a arrays
    XML_layer_thick_list = [];  #list of surface layers declared in XML

    #define import list of stacking methods
    stacking_strat_list = [];
    # bottom layer is fixed, placing 1 as default.
    stacking_strat_list.append(1)

    #define XML import step list of a arrays
    XML_step_list = [];  #list of extrusions steps per layer declared in XML

    #retrieve all the layers defined in the xml files
    layers = mydoc.getElementsByTagName("layer")

    #for each layer get the single and total thickness
    tot_thick=0
    for layer in layers:

      #retrieve the thickness of each layer
      thick = layer.getElementsByTagName("thick")[0];
      XML_layer_thick_list.append(float(thick.firstChild.data))
      tot_thick= tot_thick + float(thick.firstChild.data)

      #retrieve the stacking strategy for each layer
      try:
        stack_tmp = layer.getElementsByTagName("stack")[0];
        stacking_strat_list.append(int(stack_tmp.firstChild.data))
      except:
        stacking_strat_list.append(1)
        
      #retrieve the step number for each layer
      step_tmp = layer.getElementsByTagName("step")[0];
      XML_step_list.append(int(step_tmp.firstChild.data))

    #stacking information for top layer
    try:
        lay_sup = mydoc.getElementsByTagName("superiore")[0];
        stack_tmp = lay_sup.getElementsByTagName("stack")[0];
        stacking_strat_list.append(int(stack_tmp.firstChild.data))
    except:
        stacking_strat_list.append(1)

    # bolt generation logical trigger
    try:
      loadEps = int( mydoc.getElementsByTagName("fem_settings")[0].getElementsByTagName("loadEps")[0].firstChild.nodeValue )
      boltGen = 1
      print('BOLT GENERATION ACTIVATED')
    except:
        boltGen = 0  # no bolt generation in older XMLs
        print('BOLT GENERATION DISACTIVATED')

    #initialise load vector to 0
    load_X = 0
    load_Y = 0
    load_Z = 0

    # retrieve loading direction ( it is a vector X Y Z)
    loadDirection = str(mydoc.getElementsByTagName("loadDirection")[0].firstChild.data)


    if (loadDirection == "X+"):
            print("X+ case")
            load_X = 1
            load_Y = 0
            load_Z = 0
    elif (loadDirection == "X-"):
            print("X- case")
            load_X = -1
            load_Y = 0
            load_Z = 0
    elif (loadDirection == "Y+"):
            print("Y+ case")
            load_X = 0
            load_Y = 1
            load_Z = 0
    elif (loadDirection == "Y-"):
            print("Y- case")
            load_X = 0
            load_Y = -1
            load_Z = 0
    elif (loadDirection == "Z-"):
            print("Z+ case")
            load_X = 0
            load_Y = 0
            load_Z = 1
    elif (loadDirection == "Z-"):
            print("Z- case")
            load_X = 0
            load_Y = 0
            load_Z = -1

    # check
    if(abs(load_X+load_Y+load_Z)== 0):
      print("ERROR - LOAD VECTOR CAN'T BE NULL")

    # retrieve manual bounding layers logical, if True there are already INFERIORE and SUPERIORE surfaces 
    man_bounding= str(mydoc.getElementsByTagName("mesh_settings")[0].getElementsByTagName("man_bounding")[0].firstChild.data)
    print("MANUAL BOUNDING SET TO " + str(man_bounding) )


    ##################################################
    ## 1    END LOAD VARIABLES
    ##################################################

    ##################################################
    ### 2   GEOMETRY MODULE
    ##################################################

    import GEOM
    from salome.geom import geomBuilder
    import math
    import SALOMEDS

    geompy = geomBuilder.New()

    #generation of load vector
    LoadV = geompy.MakeVectorDXDYDZ(load_X, load_Y, load_Z)
    #geompy.addToStudy( LoadV, 'Load_Direction' )

    #CHECK if there is a configurated geometry
    aList = salome.myStudy.FindObjectByName("ASSIEME","GEOM")

    if len(aList) > 0:
       print("FOUND ASSIEME GEOMETRY -- OK")
       SObject = aList[0]
       Geometry = SObject.GetObject()  #name of the overall assemble 

    #CHECK all LAYER names
    layer_geo_list = [];   #list of all the geometry layers (that are named LAYER_n ) - USED FOR "GROUPS ON GEOMETRY" IN MESH
    vincoli_geo_list = []; #list of 1d vincoli groups - USED FOR "GROUPS ON GEOMETRY" IN MESH

    for i in range(len(layers)):

      aList = salome.myStudy.FindObjectByName( "LAYER_" + str( i + 1 ), "GEOM" )
      
      if len(aList) > 0:
      
         print("FOUND LAYER_" + str(i+1) + " GEOMETRY SURFACE")
         
         SObject = aList[0]
         layer_geo_list.append(SObject.GetObject())
             
         geompy.addToStudyInFather( layer_geo_list[i], SObject.GetObject(), 'contact_slave_' + str(i))  #every bottom surface is the slave of the lower one
        # vincoli_group = salome.myStudy.FindObjectByName("VINCOLO_"+str(i+1),"GEOM")
        # if len(vincoli_group) > 0:
        #   print("FOUND VINCOLO_"+str(i+1)+" GROUP IN LAYER_"+str(i+1))
        #   SObject = vincoli_group[0]
        #   vincoli_geo_list.append(SObject.GetObject())

        # else:
        #   print("!!! ERROR !!! NOT FOUND VINCOLO_"+str(i+1)+" GROUP IN LAYER_"+str(i+1))


    # CHECK VINCOLI group inside geometry
    aList = salome.myStudy.FindObjectByName( "VINCOLI","GEOM" )

    if len(aList) > 0:

       print("FOUND VINCOLI")
       
       SObject = aList[0]
       Vincoli = SObject.GetObject()
       
       
    # PRENDIAMO GLI ID DEI BULLONI DEL GRUPPO
    try:

     idsVincoli = geompy.GetObjectIDs( Vincoli)  #id list of all VINCOLI edges
       
    except NameError:
       print("*** VINCOLI NOT FOUND ***")
       idsVincoli=[]


    # FIND THE VINCOLI FOR EACH LAYER AND PREPARE GROUPS FOR FUTURE MESHING

    #### DEFINING AND NUMBERING VINCOLI OF LAYERS
    # -> let's find touching edges (dist=0) and assembly them as holes

    # declare an empty list for each coupled hole edges
    lista_fori = []

    #let's sort the vincoli's list
    idsVincoli.sort()

    for i in idsVincoli:

       # if the edge/face id is already in list skip to the next edge/face
       skip = False
       for liste in lista_fori:
           if ( liste.count( i) > 0 ):
             skip = True

       if skip:
          continue
          
       # if the edge id i is not already added... add i to fori_tmp
       fori_tmp = []
       fori_tmp.append( i )
       
       # check all other edge id with j index
       for j in idsVincoli:
          if j <= i:
             continue

          Curva_2 = geompy.CreateGroup( Geometry, geompy.ShapeType["EDGE"] )
          geompy.UnionIDs( Curva_2, [ j] )
          
          #if Curva2 is near to at least one of the element of foro_tmp
          for foroid in fori_tmp:
          
            #Curva1 is, every time, an element already added in fori_tmp
            Curva_1 = geompy.CreateGroup( Geometry, geompy.ShapeType["EDGE"] )
            geompy.UnionIDs( Curva_1, [ foroid] )

            dist = geompy.MinDistance( Curva_1, Curva_2)
        
        #if the distance between edge/face i and j is 0 = they are part of the same hole!
            if dist < 1e-6:
            
              #if it is already in the foro_tmp list don't add it 2 times, just go on
              if(fori_tmp.count(j) > 0 ):
                 continue
                
              fori_tmp.append( j )   #so add also edge id j to the fori_tmp

       lista_fori.append( fori_tmp)  #add the foro_tmp in the fori list

    print("FOUND N. ", len( lista_fori ) , " CIRCULAR VINCOLI")
    print(" CIRCULAR VINCOLI LIST: ", lista_fori)

    #LISTA_FORI is randomly generated. Later on the code implies that the fori are already aligned
    # FOR THIS WE ALIGN THE LISTAFORI AT THIS STAGE
    # We loop among FORI and we take only those where angle between FORI BARICENTERs and LOADV is close to 0 or to 180
    lista_fori_ordered = []

    for foro in lista_fori:
       tmp_group_1 = geompy.CreateGroup(Geometry, geompy.ShapeType["EDGE"])
       geompy.UnionIDs( tmp_group_1, foro )
       Baricentro_foro = geompy.MakeCDG( tmp_group_1 )

       #if foro is already present we skip it
       if ( lista_fori_ordered.count( foro ) > 0 ):
           continue

       lista_fori_ordered.append( foro )

       for foro_aligned in lista_fori:
       
          #skip if it is the same node
          if ( foro == foro_aligned ):
             continue

          tmp_group_2 = geompy.CreateGroup(Geometry, geompy.ShapeType["EDGE"])
          geompy.UnionIDs( tmp_group_2, foro_aligned )
          Baricentro_foro_aligned = geompy.MakeCDG( tmp_group_2 )

          #TODO - old method, to remove in future versions
          #If angle with the load direction is close to 0 or to 180 deg then we add the nodes to the list
          #Vector_1 = geompy.MakeVector( Baricentro_foro, Baricentro_foro_aligned )
          #angle = geompy.GetAngle( Vector_1, LoadV )
          #if ( abs( angle - 180 ) < 10 or abs( angle ) < 10 ):
             
          #check distance on the perpendicular plane to the loadDirection
          coord1 = geompy.PointCoordinates(Baricentro_foro)
          coord2 = geompy.PointCoordinates(Baricentro_foro_aligned)

          #calculate the distance on the plane perpendicular
          distOnPlane = numpy.sqrt((1-abs(load_X))*numpy.power(coord1[0]-coord2[0],2 ) + (1-abs(load_Y))*numpy.power(coord1[1]-coord2[1], 2) + (1-abs(load_Z))*numpy.power(coord1[2]-coord2[2],2 ) ) 
          print(distOnPlane)
          #if it is smaller than 5 mm than consider it is aligned
          if distOnPlane <= 0.005 :
            lista_fori_ordered.append( foro_aligned )
            print( str( foro ) + " aligned with " + str( foro_aligned )+" distance on plane = " + str(distOnPlane) )

    #VERIFICA FINALE
    if len( lista_fori ) != len( lista_fori_ordered ):
        print( "***ERROR*** VINCOLI ALIGNMENT FAILED" )
        stop 

    lista_fori = []
    lista_fori = lista_fori_ordered

    ############################
    # ALLOCATING ARRAYS TO BUILD REFERENCE BETWEEN EACH FORO AND ITS INTERNAL NODE
    # we need to use a list of list

    #overall 1D list (list of list) it contains list of single layer boundary
    vinco_1D_list= []
      
    #overall 0D list (list of list) it contains list of single central node for vincoli boundary
    vinco_0D_list= []    #nodi baricentro

    #number of bulloni per layer list, remember layer0 is NOT inferiore
    nBulloni_list = []

    ############################

    # Create VINCOLI sub groups for each layer, named generally vinL1D_LAYERID_LOCALID, each one with a center node vinL0DC_LAYERID_LOCALID

    #for every layer 
    for i in range(len(layers)):
      
      #empty list of circular vincoli 1D per layer ('Lay' tag)
      vincoLay_1D_list= [] 

      #empty list of circular vincoli 1D names of the layer
      nameVincoLay_1D_list= []
      
      #empty list of 0D node of vincoli per layer
      vincoLay_0D_list= []
      
      localIDBullone=0

      # check if every hole is part of the layer i'm iterating now
      for j in range( len(lista_fori) ):
      
        #create a foro temporary object as a group of the overall geometry
        foro_tmp= geompy.CreateGroup( Geometry, geompy.ShapeType["EDGE"] )
        geompy.UnionIDs( foro_tmp, lista_fori[j] )
        
        #calculate the distance between the foro_tmp and the layer we are scrolling
        dist = geompy.MinDistance( layer_geo_list[i], foro_tmp)
        
        #if distance is almost null it is part of the layer
        if dist < 1e-6:
         
          # add it to the vincoli list for each layer
          vincoLay_1D_list.append(foro_tmp)
          
          # at the same time save the name of such 1D boundary
          nameVincoLay_1D_list.append('vinL1D_' + str(i+1) + '_' + str(localIDBullone))
          
          #forse da rimuovere
          #aList = salome.myStudy.FindObjectByName( "LAYER_" + str(i+1), "GEOM" )
          
          #if len(aList) > 0:       
          #        SObject = aList[0]
          
          #add the foro_tmp as subGroup of the Layer              
          geompy.addToStudyInFather( layer_geo_list[i], vincoLay_1D_list[localIDBullone], nameVincoLay_1D_list[localIDBullone] )  
               
          # create the reference node for the 1D VINCOLO 
          vincoLay_0D_list.append( geompy.MakeCDG(vincoLay_1D_list[localIDBullone]) )
          geompy.addToStudy( vincoLay_0D_list[localIDBullone], 'vinL0DC_' + str( i + 1 ) + '_' + str(localIDBullone) )
          
          localIDBullone = localIDBullone + 1
      
      #add the vincoli list for the layer to the list of lists    
      vinco_1D_list.append(vincoLay_1D_list)
      
      #add the node list for the layer to the list of lists 
      vinco_0D_list.append(vincoLay_0D_list)
     
      #save the number of Bulloni in the layer
      nBulloni_list.append(localIDBullone)

      #if maxNBulloni!=(XML_nBulloni_list[i]):
      print('**** in LAYER_' + str(i+1) + ' : have been found = ' + str( nBulloni_list[i] ) + ' bolts!' ) 


    ####  END WITH ALL LAYERS ######################################

    ######################################
    ## PREPARING INFERIORE AND SUPERIORE SURFACES 
    ######################################

    ######################################
    #AUTOMATIC INFERIORE AND SUPERIORE

    #here we save the edges lists for each SUPERIORE vincoli (we add the geometry object this time not the ID) 
    # it works both for AUTO or MAN BOUNDING
    lista_fori_sup = []
    lista_fori_inf = []
    #### BOUNDING BOX TO LOAD SURFACES : in case we want an automatic calculation of bounding surfaces
    if man_bounding == 'False' or man_bounding == 'false'  : 

      #create bounding box
      Bounding_Box_1 = geompy.MakeBoundingBox(Geometry, True)
      
      # gravity center for the bounding box, to scale it
      Point_1 = geompy.MakeCDG(Bounding_Box_1)
      
      #increase the bounding box to consider final thickness of layers
      Bounding_Box_1 = geompy.MakeScaleAlongAxes(Bounding_Box_1, Point_1, (1+0.2*load_X), (1+0.2*load_Y), (1+0.2*load_Z)  )
      
      #explode faces to find the 2 perpendicular to LoadV
      faces = geompy.ExtractShapes(Bounding_Box_1, geompy.ShapeType["FACE"], True)

      #find the 2 coaxial surfaces
      for i in range(len(faces)):
      
        try:
          vectorN = geompy.GetNormal(faces[i])
          angle= geompy.GetAngle( LoadV, vectorN)     
         
          if ( angle == 180 ):
          
            listFaceIDs = []
            listFaceIDs.append(geompy.GetSubShapeID(Bounding_Box_1, faces[i]))
            surf_down = geompy.CreateGroup(Bounding_Box_1, geompy.ShapeType["FACE"])
            geompy.UnionIDs(surf_down, listFaceIDs)        
     
          if ( angle == 0 ):
          
            listFaceIDs = []
            listFaceIDs.append(geompy.GetSubShapeID(Bounding_Box_1, faces[i]))
            surf_up = geompy.CreateGroup(Bounding_Box_1, geompy.ShapeType["FACE"])
            geompy.UnionIDs(surf_up, listFaceIDs)
            
             
        except:     
        
          print('error with face_'+str(i) )

      ### adding VINCOLI to INFERIORE and SUPERIORE
      
      # generate a face for each vincoli
      faceVincoli = geompy.MakeFaceWires([Vincoli], 1)  
      
      #extrude all the faces (many of them overlapping)
      extrudedVincoli = geompy.MakePrismVecH2Ways(faceVincoli, LoadV, 1) 
      
      #explode the extruded compound in single solids (avoid self intersections)
      listExtrudedVincoli = geompy.ExtractShapes(extrudedVincoli, geompy.ShapeType["SOLID"], True) 

      #cut INFERIORE and SUPERIORE with each one of extruded VINCOLI 
      for i in range(len(listExtrudedVincoli)):
      
        Cut_inf = geompy.MakeCutList(surf_down, [listExtrudedVincoli[i]], False)
        surf_down = Cut_inf
        
        Cut_sup = geompy.MakeCutList(surf_up, [listExtrudedVincoli[i]], False)
        surf_up = Cut_sup
        
      # add generated SUPERIORE and INFERIORE with added VINCOLI
      geompy.addToStudy( surf_up, 'SUPERIORE' )
      geompy.addToStudy( surf_down, 'INFERIORE' )
      
      #take all the edges of surf_up (SUPERIORE)
      listEdgeTemp = geompy.ExtractShapes(surf_down, geompy.ShapeType["EDGE"], True) 
     
      lista_fori_inf = []
      
      count=0
      for i in listEdgeTemp:
        
        dist = geompy.MinDistance( i, extrudedVincoli )
        if dist < 1e-6:
        
          skip = False
          # if the edge/face id is already in list skip to the next edge/face
          
          for liste in lista_fori_inf:
          
            if ( liste.count( geompy.GetSubShapeID(surf_down, i)) > 0 ):
              skip = True          
              
          if skip:      
            continue 
               
          #if the edge is not already listed in another hole..     
          count=count+1
          lista_tmp= []
          
          #we take the id of the edge touching an extruded vincolo
          id1_temp= geompy.GetSubShapeID(surf_down, i)
          lista_tmp.append(id1_temp)
          
          Curva_1 = geompy.CreateGroup( surf_down, geompy.ShapeType["EDGE"] )
          geompy.UnionIDs( Curva_1, [id1_temp] )
          
          #now check if any other edge of the shape is in touch with the ith edge (edges of the same hole)
          for j in listEdgeTemp:
          
            id2_temp = geompy.GetSubShapeID(surf_down, j)
            
            if id2_temp == id1_temp:  #in case it is the same edge of i
              continue         
            
            Curva_2 = geompy.CreateGroup( surf_down, geompy.ShapeType["EDGE"] )
            geompy.UnionIDs( Curva_2, [ id2_temp] )
          
            #check if they are touching by calculate distance
            dist2 = geompy.MinDistance( Curva_1, Curva_2)
        
            #if the distance between edge/face i and j is 0 = they are part of the same hole!
            if dist2 < 1e-6:
               lista_tmp.append( id2_temp )   #so add also edge id j to the hole

          lista_fori_inf.append( lista_tmp)  #add the foro_tmp in the fori list
         
          #create a temporary group to be saved as child
          foro_tmp= geompy.CreateGroup( surf_down, geompy.ShapeType["EDGE"] )
          geompy.UnionIDs( foro_tmp, lista_fori_inf[count-1] )
         
          #name it as vinS1D_count
          geompy.addToStudyInFather( surf_down, foro_tmp, 'vinI1D_'+str(count))
         
    #####  NOW do the same with Superiore

      #take all the edges of surf_up (SUPERIORE)
      listEdgeTemp = geompy.ExtractShapes(surf_up, geompy.ShapeType["EDGE"], True) 
      
      #here we save the IDs of edges for each SUPERIORE vincoli (each ID is the id of a edge of a hole) 
      listaID_fori_sup = []
     

      #number of bulloni for SUPERIORE LAYER
      localIDBullone=0
      
      #here we save the nodes for SUPERIORE vincoli  
      lista0D_tmp = []
      
      for i in listEdgeTemp:
      
        dist = geompy.MinDistance( i, extrudedVincoli)
        if dist < 1e-6:
        
          skip = False
          # if the edge/face id is already in list skip to the next edge/face
          
          for liste in listaID_fori_sup:
          
            if ( liste.count( geompy.GetSubShapeID(surf_up, i)) > 0 ):
              skip = True          
              
          if skip:      
            continue 
               
          #if the edge is not already listed in another hole..     

          lista_tmp= []

          
          #we take the id of the edge touching an extruded vincolo
          id1_temp= geompy.GetSubShapeID(surf_up, i)
          lista_tmp.append(id1_temp)
          
          Curva_1 = geompy.CreateGroup( surf_up, geompy.ShapeType["EDGE"] )
          geompy.UnionIDs( Curva_1, [id1_temp] )
          
          #now check if any other edge of the shape is in touch with the ith edge (edges of the same hole)
          for j in listEdgeTemp:
          
            id2_temp = geompy.GetSubShapeID(surf_up, j)
            
            if id2_temp == id1_temp:  #in case it is the same edge of i
              continue         
            
            Curva_2 = geompy.CreateGroup( surf_up, geompy.ShapeType["EDGE"] )
            geompy.UnionIDs( Curva_2, [ id2_temp] )
          
            #check if they are touching by calculate distance
            dist2 = geompy.MinDistance( Curva_1, Curva_2)
        
            #if the distance between edge/face i and j is 0 = they are part of the same hole!
            if dist2 < 1e-6:
               lista_tmp.append( id2_temp )   #so add also edge id j to the hole

          listaID_fori_sup.append( lista_tmp)  #add the lista_tmp in the fori list
         
          #create a temporary group to be saved as child
          foro_tmp= geompy.CreateGroup( surf_up, geompy.ShapeType["EDGE"] )
          geompy.UnionIDs( foro_tmp, listaID_fori_sup[count] )
          
          #we add the geometrical object (not the ID list) to the list for SUPERIORE
          lista_fori_sup.append( foro_tmp) 
         
          #name it as vinS1D_count
          geompy.addToStudyInFather( surf_up, foro_tmp, 'vinL1D_' + str(len(layers)+1) + '_' + str(count))
          
          #create the reference node for the 1D VINCOLO, one each vinS1D_
          lista0D_tmp.append( geompy.MakeCDG(foro_tmp) )
          geompy.addToStudy( lista0D_tmp[count], 'vinL0DC_' + str(len(layers)+1) + '_' + str(count) )
          
          
          #update the BULLONI counter
          localIDBullone=localIDBullone+1
          
      #save the number of Bulloni as the last layer
      nBulloni_list.append(localIDBullone)
      var= len(nBulloni_list)
      print('**** in LAYER_'+str(var)+' (SUPERIORE AUTOMATIC) have been found = ' + str(nBulloni_list[var-1]) + ' bolts!' )

    # END AUTOMATIC BOUNDING 
    ######################################

    ######################################
    #USER DEFINED / MANUAL INFERIORE AND SUPERIORE
    # TO COMPLETE 

    #in case we supply the bounding surfaces we have to call them SUPERIORE and INFERIORE
    #remember no real bool can be inserted in xml so check with a string
    elif man_bounding== 'True' or man_bounding== 'true'  :  

      ##############  FIND VINCOLIS IN SUPERIORE  ##################################################    
      aList = salome.myStudy.FindObjectByName("SUPERIORE","GEOM")
      if len(aList) > 0:
         print("FOUND SUPERIORE BOUNDING GEOMETRY")
         SObject = aList[0]
         surf_up = SObject.GetObject()

      aList = salome.myStudy.FindObjectByName("INFERIORE","GEOM")
      if len(aList) > 0:
         print("FOUND INFERIORE BOUNDING GEOMETRY")
         SObject = aList[0]
         surf_down = SObject.GetObject()
         
      # WE NEED TO FIND WHICH OF VINCOLI ARE PARTS OF SUPERIORE   

      #empty list of circular vincoli 1D per layer ('Lay' tag)
      vincoLay_1D_list= [] 

      #empty list of circular vincoli 1D names of the layer
      nameVincoLay_1D_list= []
      
      #empty list of 0D node of vincoli per layer
      vincoLay_0D_list= []
      
      #number of bulloni for SUPERIORE LAYER
      localIDBullone = 0

      # check if every hole is part of the layer i'm iterating now
      for i in range( len(lista_fori) ):
        dist=100

        try:
          #create a foro temporary object as a group of the SUPERIORE geometry
          foro_tmp = geompy.CreateGroup( Geometry, geompy.ShapeType["EDGE"] )
          geompy.UnionIDs( foro_tmp, lista_fori[i] )
        
          #calculate the distance between the foro_tmp and the layer we are scrolling
          dist = geompy.MinDistance(surf_up, foro_tmp)
          
        except:
          print("***ERROR*** in checking if hole " + str(i) + " is part of the layer")
          continue
        
        #if distance is almost null it is part of the layer
        if dist < 1e-6:
        
          # add it to the vincoli list for each layer
          vincoLay_1D_list.append(foro_tmp)
          
          # at the same time save the name of such 1D boundary
          nameVincoLay_1D_list.append( 'vinL1D_' + str(len(layers)+1) + '_' + str(localIDBullone))
     
          #add the foro_tmp as subGroup of the Layer SUPERIORE              
          geompy.addToStudyInFather( surf_up, vincoLay_1D_list[localIDBullone],nameVincoLay_1D_list[localIDBullone] )  
          
          #we add the geometrical object (not the ID list) to the list for SUPERIORE, as well as in AUTOBOUNDING
          lista_fori_sup.append( foro_tmp)
          
          # create the reference node for the 1D VINCOLO 
          vincoLay_0D_list.append( geompy.MakeCDG(vincoLay_1D_list[localIDBullone]) )
          geompy.addToStudy( vincoLay_0D_list[localIDBullone], 'vinL0DC_' + str( len(layers) + 1) + '_' + str(localIDBullone) )
          
          # prepare the localIDBullone for the next one
          localIDBullone = localIDBullone + 1
      
      #add the vincoli list for the layer to the list of lists    
      vinco_1D_list.append(vincoLay_1D_list)
      
      #add the node list for the layer to the list of lists 
      vinco_0D_list.append(vincoLay_0D_list)
     
      #save the number of Bulloni as the last layer
      nBulloni_list.append(localIDBullone)
      var= len(nBulloni_list)
      print('**** in LAYER_'+str(var)+' (SUPERIORE MANUAL) have been found = '+str(nBulloni_list[var-1])+' bolts!' ) 
      ############## / FIND VINCOLIS IN SUPERIORE  ##################################################      
      
      ##############  FIND VINCOLIS IN INFERIORE  ##################################################
      aList = salome.myStudy.FindObjectByName("INFERIORE","GEOM")
      if len(aList) > 0:
         print("FOUND INFERIORE BOUNDING GEOMETRY")
         SObject = aList[0]
         surf_down = SObject.GetObject()   
         
      # WE NEED TO FIND WHICH OF VINCOLI ARE PARTS OF INFERIORE   

      #empty list of circular vincoli 1D per layer ('Lay' tag)
      vincoLay_1D_list= [] 

      #empty list of circular vincoli 1D names of the layer
      nameVincoLay_1D_list= []
      
      #empty list of 0D node of vincoli per layer
      vincoLay_0D_list= []
      
      #number of bulloni for SUPERIORE LAYER
      localIDBullone=0

      # check if every hole is part of the layer i'm iterating now
      for i in range(len(lista_fori)):

        dist=100
        try:
          #create a foro temporary object as a group of the SUPERIORE geometry
          foro_tmp= geompy.CreateGroup( Geometry, geompy.ShapeType["EDGE"] )
          geompy.UnionIDs( foro_tmp, lista_fori[i] )
        
          #calculate the distance between the foro_tmp and the layer we are scrolling (surf_down)
          dist = geompy.MinDistance(surf_down, foro_tmp)
          
        except:
          print("***ERROR*** in checking if hole " + str(i)+" is part of the layer")
          continue
        
        #if distance is almost null it is part of the layer
        if dist < 1e-6:
         
          # add it to the vincoli list for each layer
          vincoLay_1D_list.append( foro_tmp)
          
          # at the same time save the name of such 1D boundary
          nameVincoLay_1D_list.append('vinL1D_0_' + str(localIDBullone))
     
          #add the foro_tmp as subGroup of the Layer SUPERIORE              
          geompy.addToStudyInFather( surf_down, vincoLay_1D_list[localIDBullone], nameVincoLay_1D_list[localIDBullone] )  
          
          #we add the geometrical object (not the ID list) to the list for SUPERIORE, as well as in AUTOBOUNDING
          lista_fori_inf.append( foro_tmp)
          
          # create the reference node for the 1D VINCOLO 
          vincoLay_0D_list.append( geompy.MakeCDG( vincoLay_1D_list[localIDBullone] ) )
          geompy.addToStudy( vincoLay_0D_list[localIDBullone], 'vinL0DC_0_' + str(localIDBullone) )
          
          # prepare the localIDBullone for the next one
          localIDBullone = localIDBullone + 1

      
      #add the vincoli list for the layer to the list of lists    
      vinco_1D_list.append( vincoLay_1D_list )
      
      #add the node list for the layer to the list of lists 
      vinco_0D_list.append( vincoLay_0D_list )
     
      #save the number of Bulloni as the last layer
      nBulloni_list.append( localIDBullone )
      var = len(nBulloni_list)
      print('**** in LAYER_' + str(var) + ' (INFERIORE MANUAL) have been found = ' + str( nBulloni_list[var-1]) + ' bolts!' )
      
      ##############  /FIND VINCOLIS IN INFERIORE  ##################################################

    # declare surfaces as contact masters.
    geompy.addToStudyInFather( surf_down, surf_down, 'contact_master_0')

    if(len(layer_geo_list)>0):
      geompy.addToStudyInFather( surf_up, surf_up, 'contact_master_'+str(len(layers)))
      
    #in case no layers between inferiore or superiore are found  
    else:
      geompy.addToStudyInFather( surf_up, surf_up, 'contact_slave_0')

    #if there is a PRESSURE area copy it in SUPERIORE 
    try: 
      #CHECK if there is a configurated geometry
      aList = salome.myStudy.FindObjectByName("PRESSURE","GEOM")

      if len(aList) > 0:
        print("FOUND PRESSURE GEOMETRY -- OK")
        SObject = aList[0]
        pres_1 = SObject.GetObject()  #name of the overall assemble 

        geompy.addToStudyInFather( surf_up, pres_1, 'PRESSURE' )
        
    except:
      print(' NO PRESSURE BOUNDARY CONDITION FOUND !! ')

    # ESPORTA PROPRIETA' IN XML FILE
    # calculate LOAD area
    #props = geompy.BasicProperties(surf_up)

    # Search for the 'NCerniere' tag
    ncerniere_elements = mydoc.getElementsByTagName("NCerniere")

    if len(ncerniere_elements) == 0:
        # If 'NCerniere' does not exist, create it
        femSettings = mydoc.getElementsByTagName("fem_settings")
        
        new_ncerniere = mydoc.createElement("NCerniere")
        new_ncerniere.appendChild( mydoc.createTextNode(str(nBulloni_list[var-1])) )
        
        femSettings[0].appendChild(new_ncerniere)

    else:
        # modifying the value of a tag(here "NCerniere")
        mydoc.getElementsByTagName( "NCerniere" )[ 0 ].childNodes[ 0 ].nodeValue = str(nBulloni_list[var-1])

      

    # export the updated value
    with open(work_path + '/FEM_input.xml', "w") as xml_file:
        mydoc.writexml(xml_file)


    ##################################
    # UPDATE SALOME
    if salome.sg.hasDesktop():
      salome.sg.updateObjBrowser()

    ########################################################################################################################################
    ### SMESH component
    ### PREPARING MESH
    ########################################################################################################################################


    import  SMESH, SALOMEDS
    from salome.smesh import smeshBuilder

    smesh = smeshBuilder.New()
    #smesh.SetEnablePublish( False ) # Set to False to avoid publish in study if not needed or in some particular situations:
                                     # multiples meshes built in parallel, complex and numerous mesh edition (performance)
                                     
    print('PREPARING MESHES ----- ' )
    #----------------

    print('1 - LAYER MESH LOOP  ----- ' )

    #preparing lists of generated meshes
    mesh_layer_list = [];
    netgen1d2d_list = [];
    mesh_surface_layers_group = [];
    vincoli_1d_group = []; 


    mesh_extruded_top_2D = [];  # \E8 la superficie "top" dell'estrusione   CHECK SE USATO
    mesh_extruded_volumes_1D = [];  # \E8 una superficie perch\E8 \E8 l'estrusione di una linea   CHECK SE USATO
    mesh_extruded_volumes_2D = []; # \E8 un volume 3D perch\E8 \E8 l'estrusione di una superficie  CHECK SE USATO


    #dummy mesh
    Mesh_3d= smesh.Mesh(surf_down)

    #IMPORT MESH PARAMETERS FROM XML    ###################################################################

    #retrieve all the parameter for meshing layers defined in the xml files
    var_a = mydoc.getElementsByTagName("mesh_settings")[0].getElementsByTagName("mesh_layer")

    for var in var_a:
      #retrieve mesh parameters
      paraMaxSize = float(var.getElementsByTagName("MaxSize")[0].firstChild.data)
      paraMinSize = float(var.getElementsByTagName("MinSize")[0].firstChild.data)
      paraGrowthRate = float(var.getElementsByTagName("GrowthRate")[0].firstChild.data)
      paraNbSegPerEdge = float(var.getElementsByTagName("NbSegPerEdge")[0].firstChild.data)
      paraNbSegPerRadius = float(var.getElementsByTagName("NbSegPerRadius")[0].firstChild.data)
    #/IMPORT MESH PARAMETERS FROM XML    ##################################################################

    #NETGEN PARAMETERS FOR LAYER
    NETGEN_1D_2D = Mesh_3d.Triangle(algo=smeshBuilder.NETGEN_1D2D)
    NETGEN_2D_Parameters_1 = NETGEN_1D_2D.Parameters()
    NETGEN_2D_Parameters_1.SetMaxSize( paraMaxSize )
    NETGEN_2D_Parameters_1.SetMinSize( paraMinSize )
    NETGEN_2D_Parameters_1.SetSecondOrder( 0 )
    NETGEN_2D_Parameters_1.SetOptimize( 1 )
    NETGEN_2D_Parameters_1.SetFineness( 4 )
    NETGEN_2D_Parameters_1.SetGrowthRate( paraGrowthRate )
    NETGEN_2D_Parameters_1.SetNbSegPerEdge( paraNbSegPerEdge )
    NETGEN_2D_Parameters_1.SetNbSegPerRadius( paraNbSegPerRadius )
    NETGEN_2D_Parameters_1.SetChordalError( -1 )
    NETGEN_2D_Parameters_1.SetChordalErrorEnabled( 0 )
    NETGEN_2D_Parameters_1.SetUseSurfaceCurvature( 1 )
    NETGEN_2D_Parameters_1.SetFuseEdges( 1 )
    NETGEN_2D_Parameters_1.SetWorstElemMeasure( 21905 )
    NETGEN_2D_Parameters_1.SetUseDelauney( 0 )
    NETGEN_2D_Parameters_1.SetCheckChartBoundary( 0 )
    NETGEN_2D_Parameters_1.SetQuadAllowed( 0 )
    #----------------------------

    # MESHING ALL LAYERS

    # meshing all layers in layer_geo_list (excluding thus INFERIORE and SUPERIORE)

    for i in range(len(layer_geo_list)):

      print('Meshing layer N.' +str(i+1))
      
      mesh_layer_list.append(smesh.Mesh(layer_geo_list[i]))
      
      #use standard mesh parameters
      status = mesh_layer_list[i].AddHypothesis(NETGEN_2D_Parameters_1)
      netgen1d2d_list.append(mesh_layer_list[i].Triangle(algo=smeshBuilder.NETGEN_1D2D) )
      
      ##compute mesh
      try:  
        isDone = mesh_layer_list[i].Compute() 
      except:
        print('ERROR IN MESHING LAYER_'+str(i+1))

      ## Set the name of the layer mesh 
      smesh.SetName(mesh_layer_list[i].GetMesh(), 'Mesh_layer_' + str(i+1) )

      ## CREATE GROUPS FROM GEOMETRY FOR EACH LAYER (2D-1D-0D)
       
      # 2D GROUPS- create the surface 2D contact groups by importing from GEO
      mesh_surface_layers_group.append(mesh_layer_list[i].GroupOnGeom( layer_geo_list[i], 'contact_slave_' + str(i), SMESH.FACE) )
      smesh.SetName( mesh_surface_layers_group[i], 'contact_slave_' + str(i))
      
      # 1D GROUPS vincoli 1D groups by scrolling the list of lists (importing from GEO): 
      vincoli_1d_group = []; 
      vincoli_0dlayer_group = [];
      
      # list per layer of all baricentral 0D nodes of 1D vincoli
      mesh_layer_0d_list = [];  
      
      #seeking all nodes in the layer (jth node in ith layer)
      for j in range( len( vinco_1D_list[i] ) ):
      
        try:
          #append group from GEO from the overall vinco_1D_list the ith layer and the its jth edge
          #remember here we have to provide the geometry elements, not the IDs = vinco_1D_list[i][j]
          vincoli_1d_group.append(mesh_layer_list[i].GroupOnGeom( vinco_1D_list[i][j], 'vinL1D_' + str(i+1) + '_' + str(j), SMESH.EDGE) )
          smesh.SetName(vincoli_1d_group[j], 'vinL1D_' + str(i+1) + '_' + str(j))
          
        except:
          print('***ERROR*** in importing 1D VINCOLI from GEO for layer ' + str(i+1) )
        
        # 0D GROUPS now we need to create the CENTER nodes (0D) and name them 
        #find the CENTER node 
        aList = salome.myStudy.FindObjectByName('vinL0DC_' + str(i+1) + '_' + str(j),"GEOM")
        
        if len(aList) > 0:       
          SObject = aList[0]      
          point_tmp = SObject.GetObject()
          
          #take the coordinates
          coords = geompy.PointCoordinates(point_tmp)
          
          #generate the mesh CENTER node and take the id
          nodeID = mesh_layer_list[i].AddNode( coords[0], coords[1], coords[2] )
          
          #create the CENTER node group in the layer mesh
          mesh_layer_0d_list.append(mesh_layer_list[i].CreateEmptyGroup( SMESH.NODE, 'vinL0DC_' + str(i+1) + '_' + str(j) ) )
          nbAdd = mesh_layer_0d_list[j].Add( [ nodeID ] )
          
        else:
          print('*** ERROR IN GENERATING MESH NODE IN LAYER '+str(i+1)+' node n. '+str(j)) 
     
      ## Estrusione della mesh
      # direzioni di estrusione
      a = load_X * XML_layer_thick_list[i] / XML_step_list[i]
      b = load_Y * XML_layer_thick_list[i] / XML_step_list[i]
      c = load_Z * XML_layer_thick_list[i] / XML_step_list[i]
      try:
        output = mesh_layer_list[i].ExtrusionSweepObjects( [], [mesh_layer_list[i]], [ mesh_layer_list[i] ], [ a, b, c], XML_step_list[i], 1, [  ], 0, [  ], [  ], 0 ) 
        #[ layer_ext, vincolo_extr, layer_up, vincolo_top ]
        
        countBulloni=0  
        
        #output array has its own internal order
        for k in range(len(output)):
        
          #first we have the extruded volume (from 2d surface)
          if k==0:
            smesh.SetName(output[k], 'LAY_3D_'+(str(i+1)) )
          
          #2nd we have the extruded 1D VINCOLI
                 
          if (k>0 and k<= nBulloni_list[i]):
            smesh.SetName(output[k], 'vinL3D_'+str(i+1)+'_'+str(countBulloni) )
            countBulloni=countBulloni+1
            
          #3rd there is the 2D surface TOP = contact surface
          if k == (nBulloni_list[i]+1):
          
            if(i < len(layer_geo_list)-1):
              smesh.SetName(output[k], 'contact_master_'+(str(i+1)) )
              
            if(i == len(layer_geo_list)-1):
              smesh.SetName(output[k], 'contact_slave_'+(str(i+1)) )
            
          #after this k value other output are 1d_edge_top 
          
      except: 
        print('ERROR in extruding Mesh_layer_'+str(i+1) )

      # NOW iterate again to convert 1D to 0D, we do it now to simplify the extrusion before 
      for j in range(len(vinco_1D_list[i])):
      
        try: 
          #pick all the edges vinL1D and take only the nodes in vinL0D
          #append group from GEO from the overall vinco_1D_list the ith layer and the its jth edge
          #remember here we have to provide the geometry elements, not the IDs = vinco_1D_list[i][j]
          vincoli_0dlayer_group.append(mesh_layer_list[i].GroupOnGeom(vinco_1D_list[i][j],'vinL0D_'+str(i+1)+'_'+str(j),SMESH.NODE) )
          smesh.SetName(vincoli_0dlayer_group[j], 'vinL0D_'+str(i+1)+'_'+str(j))
          
        except:
          print('***ERROR*** in creating 0D (from edge) VINCOLI from GEO for layer ' + str(i+1) )
      
      #SAVE GASKET MESH 
      try:
        mesh_layer_list[i].ExportMED(work_path+'/Mesh_layer_'+str(i+1)+'.med',auto_groups=0,minor=40,overwrite=1,meshPart=None,autoDimension=1)
        pass
      except:
        print('ExportMED() failed. Mesh_layer_'+str(i+1)+'.med | Invalid file name?')




    print('1.1 END COMPUTING GASKET LAYER MESH ----- ' )

    #############################################


    surface_layers = [];

    print('2 PREPARING BOTTOM SURFACE MESH ----- ' )
    Mesh_surf_down = smesh.Mesh(surf_down)

    #IMPORT MESH PARAMETERS FROM XML    ###################################################################

    #retrieve all the parameter for meshing layers defined in the xml files
    var_a = mydoc.getElementsByTagName("mesh_settings")[0].getElementsByTagName("mesh_bounding")

    for var in var_a:
      #retrieve mesh parameters
      paraMaxSize = float(var.getElementsByTagName("MaxSize")[0].firstChild.data)
      paraMinSize = float(var.getElementsByTagName("MinSize")[0].firstChild.data)
      paraGrowthRate = float(var.getElementsByTagName("GrowthRate")[0].firstChild.data)
      paraNbSegPerEdge = float(var.getElementsByTagName("NbSegPerEdge")[0].firstChild.data)
      paraNbSegPerRadius = float(var.getElementsByTagName("NbSegPerRadius")[0].firstChild.data)

    #/IMPORT MESH PARAMETERS FROM XML    ###################################################################


    #NETGEN PARAMETERS FOR surfaces
    NETGEN_1D_2D_1 = Mesh_surf_down.Triangle(algo=smeshBuilder.NETGEN_1D2D)
    NETGEN_2D_Parameters_2 = NETGEN_1D_2D_1.Parameters()
    NETGEN_2D_Parameters_2.SetMaxSize( paraMaxSize )
    NETGEN_2D_Parameters_2.SetMinSize( paraMinSize )
    NETGEN_2D_Parameters_2.SetSecondOrder( 0 )
    NETGEN_2D_Parameters_2.SetOptimize( 1 )
    NETGEN_2D_Parameters_2.SetFineness( 3 )
    NETGEN_2D_Parameters_2.SetGrowthRate( paraGrowthRate )
    NETGEN_2D_Parameters_2.SetNbSegPerEdge( paraNbSegPerEdge )
    NETGEN_2D_Parameters_2.SetNbSegPerRadius( paraNbSegPerRadius )
    NETGEN_2D_Parameters_2.SetChordalError( -1 )
    NETGEN_2D_Parameters_2.SetChordalErrorEnabled( 0 )
    NETGEN_2D_Parameters_2.SetUseSurfaceCurvature( 1 )
    NETGEN_2D_Parameters_2.SetFuseEdges( 1 )
    NETGEN_2D_Parameters_2.SetWorstElemMeasure( 21905 )
    NETGEN_2D_Parameters_2.SetUseDelauney( 0 )
    NETGEN_2D_Parameters_2.SetCheckChartBoundary( 0 )
    NETGEN_2D_Parameters_2.SetQuadAllowed( 0 )
    #------------------------------

    ##compute mesh
    isDone = Mesh_surf_down.Compute()

    ## Set names of bottom surface Mesh objects
    smesh.SetName(Mesh_surf_down.GetMesh(), 'Mesh_2D_inf')
    smesh.SetName(NETGEN_1D_2D_1.GetAlgorithm(), 'NETGEN 1D-2D per superfici')
    smesh.SetName(NETGEN_2D_Parameters_2, 'NETGEN_2D_Parameters_2')

    ## Set groups on geometry 
    surface_layers.append(Mesh_surf_down.GroupOnGeom(surf_down,'contact_master_0',SMESH.FACE) )
    smesh.SetName(surface_layers[0], 'contact_master_0')

    # 1D GROUPS vincoli 1D groups by scrolling the list of lists (importing from GEO): 
    vincoli_1d_group = []; 
      
    # list per layer of all baricentral 0D nodes of 1D vincoli
    mesh_layer_0d_list = [];  
    node0DC_inf_COORDlist = [];

    #seeking all holes in the layer (ith node of INFERIORE)
    for i in range(len(lista_fori_inf)):

      try:
      
        #append 1D groups from GEO surf_up (SUPERIORE) checking hole by hole
        #remember here we have to provide the geometry elements, not the IDs
        vincoli_1d_group.append(Mesh_surf_down.GroupOnGeom(lista_fori_inf[i], 'vinL1D_0_' + str(i), SMESH.EDGE) )   
        smesh.SetName( vincoli_1d_group[i], 'vinL1D_0_' + str(i))
          
      except:
        print('***ERROR*** in importing 1D VINCOLI from GEO for INFERIORE')
        
      # 0D GROUPS now we need to create the nodes (0D) and name them 
      #find the node 
      aList = salome.myStudy.FindObjectByName( 'vinL0DC_0_' + str(i), "GEOM" )
        
      if len(aList) > 0:       
        SObject = aList[0]      
        point_tmp = SObject.GetObject()
          
        #take the coordinates
        coords = geompy.PointCoordinates(point_tmp)
          
        #generate the mesh node and take the id
        nodeID = Mesh_surf_down.AddNode( coords[0], coords[1], coords[2] )
          
        #create the node group in the layer mesh
        mesh_layer_0d_list.append(Mesh_surf_down.CreateEmptyGroup( SMESH.NODE, 'vinL0DC_0_' + str(i) ) )
        nbAdd = mesh_layer_0d_list[i].Add( [ nodeID ] )
        node0DC_inf_COORDlist.append(list(coords))
        
      else:
        print('*** ERROR IN GENERATING MESH NODE IN LAYER INFERIORE @ node n. '+str(i)) 






    ## If defined load the INFERIORE thickness
    #retrieve all the layers defined in the xml files
    try:
      inferiore = mydoc.getElementsByTagName("inferiore")

      #for each layer get the single and total thickness
      for inf in inferiore:
      
        #retrieve the thickness of INFERIORE layer
        thick_inf = float(inf.getElementsByTagName("thick")[0].firstChild.data);
        step_inf = int(inf.getElementsByTagName("step")[0].firstChild.data);

    #if not just use random thickness    
    except:
      print('ERROR - step or thick not found in INFERIORE. Using default values')
      thick_inf=0.01
      step_inf = 3


    #mesh extrusion
    a= -load_X*thick_inf/step_inf
    b= -load_Y*thick_inf/step_inf
    c= -load_Z*thick_inf/step_inf
    try:
      output= Mesh_surf_down.ExtrusionSweepObjects( [], [], [ surface_layers[0] ], [ a, b, c], step_inf, 1, [  ], 0, [  ], [  ], 0 )
      #smesh.SetName(surf_down_ext, 'fix' )   # the lower surface exterior surface is fixed
      #smesh.SetName(surf_down_vol, 'INF_3D' ) 
      countBulloniInf=0  
        
      #output array has its own internal order
      for k in range(len(output)):
        
        #first we have the extruded volume (from 2d surface)
        if k==0:
          smesh.SetName(output[k], 'INF_3D') 
          
        #2nd we have the extruded 1D VINCOLI
                 
        if (k>0 and k<= nBulloni_list[len(nBulloni_list)-1]):
          smesh.SetName(output[k], 'vinL3D_0_'+str(countBulloniInf) )
          countBulloniInf=countBulloniInf+1
            
        #3rd there is the 2D surface FIX = lower surface of INFERIORE
        if k == (nBulloni_list[len(nBulloni_list)-1]+1):
          smesh.SetName(output[k], 'fix' )

    except: 
      print('ERROR in extruding bottom surface mesh')

    #SAVE GASKET MESH 
    try:
      Mesh_surf_down.ExportMED(work_path+'/Mesh_battuta_inferiore.med',auto_groups=0,minor=40,overwrite=1,meshPart=None,autoDimension=1)
      pass
    except:
      print('ExportMED() failed. Invalid file name?')

    print('2.1 END COMPUTING BOTTOM SURFACE MESH ----- ' )

    #######################################

    print('3 PREPARING TOP SURFACE MESH ----- ' )

    Mesh_surf_up = smesh.Mesh(surf_up)

    status = Mesh_surf_up.AddHypothesis(NETGEN_2D_Parameters_2)
    NETGEN_1D_2D_2 = Mesh_surf_up.Triangle(algo=smeshBuilder.NETGEN_1D2D)

    ##compute mesh
    isDone = Mesh_surf_up.Compute() 

    ## Set names of Mesh objects
    smesh.SetName(Mesh_surf_up.GetMesh(), 'Mesh_2D_sup')

    ## Check the presence of PRESSURE
    pres_logic= False

    # old XML with PRES element
    try:
      if ( mydoc.getElementsByTagName("fem_settings")[0].getElementsByTagName("PRES")[0].firstChild.nodeValue == "True" or mydoc.getElementsByTagName("fem_settings")[0].getElementsByTagName("PRES")[0].firstChild.nodeValue == "true" ):
        pres_logic= True
        
    #new XML version with singleForce condition for "pres" group.
    except:
      singleForces = mydoc.getElementsByTagName("singleForce")
      for singleForce in singleForces:
      
        try:
          if singleForce.getElementsByTagName("surface")[0].firstChild.nodeValue == "pres":
            pres_logic= True    
            
        except:
          continue

    ## Set groups on geometry 
    if(len(layer_geo_list)>0 and pres_logic== False):
      surface_layers.append(Mesh_surf_up.GroupOnGeom(surf_up,'contact_master_'+str(len(layers)),SMESH.FACE) )
      smesh.SetName(surface_layers[1], 'contact_master_'+str(len(layers)) )

    elif(len(layer_geo_list)>0 and pres_logic== True):
      surface_layers.append(Mesh_surf_up.GroupOnGeom(surf_up,'contact_master_'+str(len(layers))+'T',SMESH.FACE) )
      smesh.SetName(surface_layers[1], 'contact_master_'+str(len(layers))+'T' )

    #in case no layers were found (or are not defined purposely)  
    else:
      surface_layers.append(Mesh_surf_up.GroupOnGeom(surf_up,'contact_slave_0',SMESH.FACE) )
      smesh.SetName(surface_layers[1], 'contact_slave_0' )

    # 1D GROUPS vincoli 1D groups by scrolling the list of lists (importing from GEO): 
    vincoli_1d_group = []; 
      
    # list per layer of all baricentral 0D nodes of 1D vincoli
    mesh_layer_0d_list = [];  
    node0DC_sup_COORDlist = [];

    #in case we had a PRESSURE surface in our SUPERIORE 

    if pres_logic:
      try:
      
        # generate a group from the geometry
        pres_mesh = Mesh_surf_up.GroupOnGeom(pres_1,'PRESSURE',SMESH.FACE)
        smesh.SetName(pres_mesh, 'pres')
        print('PRESSURE SURFACE FOUND IN SUPERIORE MESH ')

      #if not just give a warning     
      except:
        print('!!! ERROR !!! IN IMPORTING PRESSURE SURFACE ON MESH ')
      
    #seeking all holes in the layer (ith node of SUPERIORE)
    for i in range(len(lista_fori_sup)):

      try:
      
        #append 1D groups from GEO surf_up (SUPERIORE) checking hole by hole
        #remember here we have to provide the geometry elements, not the IDs
        vincoli_1d_group.append(Mesh_surf_up.GroupOnGeom(lista_fori_sup[i], 'vinL1D_' + str(len(layers)+1) + '_' + str(i), SMESH.EDGE) )   
        smesh.SetName(vincoli_1d_group[i], 'vinL1D_' + str( len(layers) + 1) + '_' + str(i))
          
      except:
        print('***ERROR*** in importing 1D VINCOLI from GEO for SUPERIORE')
        
      # 0D GROUPS now we need to create the nodes (0D) and name them 
      #find the node 
      aList = salome.myStudy.FindObjectByName('vinL0DC_' + str(len(layers)+1) + '_' + str(i), "GEOM")
        
      if len(aList) > 0:       
        SObject = aList[0]      
        point_tmp = SObject.GetObject()
          
        #take the coordinates
        coords = geompy.PointCoordinates(point_tmp)
          
        #generate the mesh node and take the id
        nodeID = Mesh_surf_up.AddNode( coords[0], coords[1], coords[2] )
          
        #create the node group in the layer mesh
        mesh_layer_0d_list.append(Mesh_surf_up.CreateEmptyGroup( SMESH.NODE, 'vinL0DC_' + str(len(layers)+1) + '_' + str(i) ) )
        nbAdd = mesh_layer_0d_list[i].Add( [ nodeID ] )
        node0DC_sup_COORDlist.append(list(coords))
        
      else:
        print('*** ERROR IN GENERATING MESH NODE IN LAYER SUPERIORE ' + str( len(layers) + 1 ) + ' node n. ' + str(i)) 


    ## If defined load the SUPERIORE thickness
    #retrieve all the layers defined in the xml files
    try:
      superiore = mydoc.getElementsByTagName("superiore") 

      #for each layer get the single and total thickness

      for sup in superiore:
      
        #retrieve the thickness of SUPERIORE layer
        thick_sup = float(sup.getElementsByTagName("thick")[0].firstChild.data);
        step_sup = int(sup.getElementsByTagName("step")[0].firstChild.data);

    #if not just use random thickness    
    except:
      thick_sup=0.01
      step_sup = 3

    #mesh extrusion parameters
    a= load_X*thick_sup/step_sup
    b= load_Y*thick_sup/step_sup
    c= load_Z*thick_sup/step_sup

    #now extrude SUPERIORE and save all the boundaries
    try:
      output= Mesh_surf_up.ExtrusionSweepObjects( [], [Mesh_surf_up], [ Mesh_surf_up ], [ a, b, c], step_sup, 1, [  ], 0, [  ], [  ], 0 )
      
      countBulloni=0  
        
      #output array has its own internal order
      for k in range(len(output)):
        
        #first we have the extruded volume (from 2d surface)
        if k==0:
          smesh.SetName(output[k], 'SUP_3D') 
          
        #2nd we have the extruded 1D VINCOLI
                 
        if (k>0 and k<= nBulloni_list[len(nBulloni_list)-1]):
          smesh.SetName(output[k], 'vinL3D_'+str(len(layers)+1)+'_'+str(countBulloni) )
          countBulloni=countBulloni+1
            
        #3rd there is the 2D surface TOP = top surface of superiore
        if k == (nBulloni_list[len(nBulloni_list)-1]+1):
          smesh.SetName(output[k], 'top_surf' )

    except: 
      print('ERROR in extruding top surface mesh')
      
    if pres_logic: 
      contact_master_SUPERIORE = Mesh_surf_up.CutListOfGroups( [ surface_layers[len(surface_layers)-1] ], [ pres_mesh ], 'contact_master_'+str(len(layers)) )
      #smesh.SetName(MESH_TENUTA, 'MESH_TENUTA')

    #SAVE GASKET MESH 
    try:
      Mesh_surf_up.ExportMED(work_path+'/Mesh_battuta_superiore.med',auto_groups=0,minor=40,overwrite=1,meshPart=None,autoDimension=1)
      pass
    except:
      print('ExportMED() failed. Invalid file name?')


    print('3.1 END COMPUTING TOP SURFACE MESH ----- ' )

    ##################################################
    ##  BUILD COMPOUND
    ##################################################


    #import previous med files
    mesh_compound_elements= [];
    for i in range(len(layer_geo_list)):
      ([mesh_import], status) = smesh.CreateMeshesFromMED(work_path+'/Mesh_layer_'+str(i+1)+'.med')
      mesh_compound_elements.append(mesh_import.GetMesh() )
      os.remove(work_path+'/Mesh_layer_'+str(i+1)+'.med')  #remove the original file

    ([Mesh_battuta_inferiore_1], status) = smesh.CreateMeshesFromMED(work_path+'/Mesh_battuta_inferiore.med' )
    mesh_compound_elements.append(Mesh_battuta_inferiore_1.GetMesh() )

    ([Mesh_battuta_superiore_1], status) = smesh.CreateMeshesFromMED(work_path+'/Mesh_battuta_superiore.med' )
    mesh_compound_elements.append(Mesh_battuta_superiore_1.GetMesh() )

    list_all_groups = [];
    #Compound_Mesh_1 = smesh.Concatenate( [ Mesh_tenuta_1.GetMesh(), Mesh_battuta_inferiore_1.GetMesh(), Mesh_battuta_superiore_1.GetMesh() ], 1, 0, 1e-05, True )
    Compound_Mesh_1 = smesh.Concatenate(  mesh_compound_elements , 1, 0, 1e-05, False )

    ## Set names of Mesh objects
    smesh.SetName(Compound_Mesh_1.GetMesh(), 'MESH_TENUTA')
    list_all_groups.append(Compound_Mesh_1.GetGroups() )


    ##################################################
    ##  SAVE FINAL MESH
    ##################################################

    print('4 EXPORT FINAL COMPOUND MESH ----- ' )
    try:
      Compound_Mesh_1.ExportMED(work_path+'/Mesh_tenuta_completa.med',auto_groups=0,minor=40,overwrite=1,meshPart=None,autoDimension=1)
      pass
    except:
      print('ExportMED() failed. Invalid file name?')
      
      
    # REMOVE EVERYTHING IN SMESH ENVIRONMENT 
    sb = salome.myStudy.NewBuilder()
    for compName in ["SMESH"]:
      comp = salome.myStudy.FindComponent(compName)
      if comp:
        iterator = salome.myStudy.NewChildIterator( comp )
        while iterator.More():
          sobj = iterator.Value()
          iterator.Next()
          sb.RemoveObjectWithChildren( sobj )
          
    #Remove all nodes vinL0DC_0_i  - for inferiore
    for nodo in range(countBulloniInf):
      try:
        obj = salome.myStudy.FindObjectByName("vinL0DC_0_" + str(nodo), "GEOM")   
        sb.RemoveObjectWithChildren(obj[0])          #select an object from the list
      except:
        continue

    #Remove all nodes vinL0DC_n_m for LAYERs and SUPERIORE
    for layer in range( len(layer_geo_list) + 1):
      for nodo in range( nBulloni_list[layer] ):
        try:
          obj = salome.myStudy.FindObjectByName("vinL0DC_" + str(layer+1) + "_" + str(nodo),"GEOM")   
          sb.RemoveObjectWithChildren(obj[0])          #select an object from the list
        except:
          continue
          
    ## Remove other mesh files from folder
    os.remove(work_path+'/Mesh_battuta_inferiore.med')
    os.remove(work_path+'/Mesh_battuta_superiore.med') 

    #RELOAD FINAL COMPOUND MESH
    ([MESH_TENUTA], status) = smesh.CreateMeshesFromMED( work_path + '/Mesh_tenuta_completa.med' )
    #mesh_compound_elements.append(MESH_TENUTA.GetMesh() )

    os.remove(work_path+'/Mesh_tenuta_completa.med') 
    ##################################################


    ##################################################
    ##  PUT ALL THE LAYERS IN CONTACT - STACKING
    ##################################################

    # common operations

    mesh_group_name_list = []
    mesh_volume_list = []
    mesh_layer0DCNodes_list = []

    #retrieve all the group from the mesh
    mesh_group_list= MESH_TENUTA.GetGroups()

    #retrieve all the group names from the mesh group list
    for group in mesh_group_list:
      mesh_group_name_list.append(group.GetName() )
      
    #declare an empty array to store bounding box informations for each layer
    mesh_bb_list = []

    # VOLUMES and their subgroups-----------------------------------------------
    #get the id of the INFERIORE group
    temp_id= [i for i,meshname in enumerate(mesh_group_name_list) if 'vinL0DC_0_' in meshname] 

    #save the INFERIORE group
    mesh_volume_list.append(mesh_group_list[temp_id[0]] )

    #add the inferiore bb tuple of six values (minX, minY, minZ, maxX, maxY, maxZ) 
    mesh_bb_list.append( smesh.BoundingBox( mesh_group_list[temp_id[0]] ) )

    # 0DC nodes ----------------------------------------------------------------
    #get the ids of the INFERIORE group 0DC nodes
    #temp_id = [meshname for meshname in mesh_group_name_list if 'vinL0DC_0_' in meshname]
    temp_ids = [i for i,meshname in enumerate(mesh_group_name_list) if 'vinL0DC_0_' in meshname] 

    # get the group for each id gathered in temp_ids
    temp_list=[]
    for id in temp_ids:
        temp_list.append(mesh_group_list[id] )
        
    #save the INFERIORE group 0DC nodes
    mesh_layer0DCNodes_list.append(temp_list)

    # LAY_3D groups
    laynum=0
    for layer in range(len(layer_geo_list)):
      
        laynum = laynum + 1 

        # VOLUMES and their subgroups-----------------------------------------------
        #get the id of the LAY_3D_ith group
        temp_id= [i for i,x in enumerate(mesh_group_name_list) if x == 'LAY_3D_' + str(laynum)] 

        #save the LAY_3D_ith group
        mesh_volume_list.append( mesh_group_list[temp_id[0]] )

        #add the LAY_3D_ith bb tuple tuple of six values (minX, minY, minZ, maxX, maxY, maxZ) 
        mesh_bb_list.append( smesh.BoundingBox( mesh_group_list[temp_id[0]] ) )
      
        # 0DC nodes ----------------------------------------------------------------
        #get the ids of each LAY_3D group 0DC nodes
        #temp_id = [meshname for meshname in mesh_group_name_list if 'vinL0DC_0_' in meshname]
        temp_ids = [i for i,meshname in enumerate(mesh_group_name_list) if 'vinL0DC_'+str(laynum)+'_' in meshname] 

        # get the group for each id gathered in temp_ids
        temp_list=[]
        for id in temp_ids:
            temp_list.append(mesh_group_list[id] )
            
        #save each LAY_3D group 0DC nodes
        mesh_layer0DCNodes_list.append(temp_list)

    # SUPERIORE

    # VOLUMES and their subgroups-----------------------------------------------
    #get the id of the SUPERIORE group
    temp_id= [i for i,x in enumerate(mesh_group_name_list) if x == 'SUP_3D'] 

    #save the SUPERIORE group
    mesh_volume_list.append(mesh_group_list[temp_id[0]] )

    #add the superiore bb tuple tuple of six values (minX, minY, minZ, maxX, maxY, maxZ) 
    mesh_bb_list.append(smesh.BoundingBox(mesh_group_list[temp_id[0]]))

    # 0DC nodes ----------------------------------------------------------------
    #get the ids of each LAY_3D group 0DC nodes
    #temp_id = [meshname for meshname in mesh_group_name_list if 'vinL0DC_0_' in meshname]
    temp_ids = [i for i,meshname in enumerate(mesh_group_name_list) if 'vinL0DC_'+str(laynum+1)+'_' in meshname] 

    # get the group for each id gathered in temp_ids
    temp_list=[]
    for id in temp_ids:
        temp_list.append(mesh_group_list[id] )
        
    #save each LAY_3D group 0DC nodes
    mesh_layer0DCNodes_list.append(temp_list)


    #prepare the overall list of thicknesses
    mesh_thick_list = []
    mesh_thick_list.append(thick_inf)
    for spessore in XML_layer_thick_list:
        mesh_thick_list.append(spessore)
    mesh_thick_list.append(thick_sup)

    ##### spacing list (according to different stacking strategies
    delta_space_list = []

    #incremental spacing referred to INFERIORE
    delta_space_inc = 0

    for i in range(len(stacking_strat_list)-1): #forse da metterci un -1

        #depending on LoadV direction (+/-) we have to follow different patterns
        if ((load_X + load_Y + load_Z) > 0):
            
            #bb tuple tuple of six values (minX, minY, minZ, maxX, maxY, maxZ)
            delta= min( (mesh_bb_list[i][3] - mesh_bb_list[i+1][0]) * abs(load_X), ( mesh_bb_list[i][4] - mesh_bb_list[i+1][1] ) * abs(load_Y), ( mesh_bb_list[i][5] - mesh_bb_list[i+1][2] ) * abs(load_Z) )
            
            # if stacking considering thickness
            if stacking_strat_list[i+1] == 2:
                delta= min( (mesh_bb_list[i][0] - mesh_bb_list[i+1][0]) * abs(load_X), ( mesh_bb_list[i][1] - mesh_bb_list[i+1][1] ) * abs(load_Y), ( mesh_bb_list[i][2] - mesh_bb_list[i+1][2] ) * abs(load_Z) )
                #stack exactly at ith level upper surface according only to the thickness
                delta = delta + mesh_thick_list[i]
        
        if ((load_X + load_Y + load_Z) < 0):
        
            #bb tuple tuple of six values (minX, minY, minZ, maxX, maxY, maxZ)
            delta= max( (mesh_bb_list[i][0] - mesh_bb_list[i+1][3]) * abs(load_X), ( mesh_bb_list[i][1] - mesh_bb_list[i+1][4] ) * abs(load_Y), ( mesh_bb_list[i][2] - mesh_bb_list[i+1][5] ) * abs(load_Z) )
                                  
            # if stacking considering thickness
            if stacking_strat_list[i+1] == 2:
                delta= max( (mesh_bb_list[i][3] - mesh_bb_list[i+1][3]) * abs(load_X), (mesh_bb_list[i][4] - mesh_bb_list[i+1][4]) * abs(load_Y), (mesh_bb_list[i][5] - mesh_bb_list[i+1][5]) * abs(load_Z) )
                #stack exactly at ith level upper surface according only to the thickness
                delta = delta - mesh_thick_list[i]
        
                
        #the new gap is the previous incremental + the current for the current layer
        delta_space_list.append( delta_space_inc + delta)  
        
        #update the incremental distance from bottom layer
        delta_space_inc = delta_space_inc + delta
        
        #moving VOLUMES and their subgroups
        MESH_TENUTA.TranslateObject( mesh_volume_list[i+1], [ delta_space_list[i] * abs(load_X), delta_space_list[i] * abs(load_Y), delta_space_list[i] * abs(load_Z) ], 0 )
        
        #moving 0DC nodes, one at a time
        for nodo in mesh_layer0DCNodes_list[i+1]:
            MESH_TENUTA.TranslateObject( nodo , [ delta_space_list[i] * abs(load_X), delta_space_list[i] * abs(load_Y), delta_space_list[i] * abs(load_Z) ], 0 )

    #UPDATING SUPERIORE COORDINATES         
    m = len(delta_space_list)-1

    for n in range(len(mesh_layer0DCNodes_list[m])):
        node0DC_sup_COORDlist[n][0] = node0DC_sup_COORDlist[n][0] + delta_space_list[m] * abs(load_X) 
        node0DC_sup_COORDlist[n][1] = node0DC_sup_COORDlist[n][1] + delta_space_list[m] * abs(load_Y) 
        node0DC_sup_COORDlist[n][2] = node0DC_sup_COORDlist[n][2] + delta_space_list[m] * abs(load_Z) 

    # MOVING INF & SUP 0DC nodes to extreme (according to their thickness) BEFORE generating BOLTS
    #inferiore
    deltaN = - mesh_thick_list[0]
    n = 0
    # each bolt of the INF layer
    for nodo in mesh_layer0DCNodes_list[0]:
        MESH_TENUTA.TranslateObject( nodo , [ deltaN * load_X, deltaN * load_Y, deltaN * load_Z ], 0 )
        node0DC_inf_COORDlist[n][0] = node0DC_inf_COORDlist[n][0] + deltaN * (load_X) 
        node0DC_inf_COORDlist[n][1] = node0DC_inf_COORDlist[n][1] + deltaN * (load_Y) 
        node0DC_inf_COORDlist[n][2] = node0DC_inf_COORDlist[n][2] + deltaN * (load_Z)
        n=n+1

    #superiore
    deltaN = mesh_thick_list[len(stacking_strat_list)-1]
    n = 0
    # each bolt of the SUP layer
    for nodo in mesh_layer0DCNodes_list[len(stacking_strat_list)-1]:
        MESH_TENUTA.TranslateObject( nodo , [ deltaN * load_X, deltaN * load_Y, deltaN * load_Z ], 0 )
        node0DC_sup_COORDlist[n][0] = node0DC_sup_COORDlist[n][0] + deltaN * (load_X) 
        node0DC_sup_COORDlist[n][1] = node0DC_sup_COORDlist[n][1] + deltaN * (load_Y) 
        node0DC_sup_COORDlist[n][2] = node0DC_sup_COORDlist[n][2] + deltaN * (load_Z)
        n=n+1
        
    # add 1D edge (bulloni) if the trigger is on
    if boltGen == 1:

        print('Generating 1d bolt elements' )
        bolts_group = []
        bolts_1d_list = []
        
        #retrieve the  XML location for custom Loads
        femSettings = mydoc.getElementsByTagName("fem_settings")[0]

        # for loop over all the bolts of INFERIORE (same number of SUPERIORE)
        var= len(nBulloni_list)
        for j in range(nBulloni_list[var-1]):
        
            temp_list = []
            
            #find the INFERIORE bolt node based on the updated coords    
            nodoID= MESH_TENUTA.FindNodeClosestTo(node0DC_inf_COORDlist[j][0], node0DC_inf_COORDlist[j][1], node0DC_inf_COORDlist[j][2]  ) 
            
            #append to node list to generate edge
            temp_list.append( nodoID )

            #find the SUPERIORE bolt node based on the updated coords    
            nodoID= MESH_TENUTA.FindNodeClosestTo(node0DC_sup_COORDlist[j][0], node0DC_sup_COORDlist[j][1], node0DC_sup_COORDlist[j][2]  )
            
            #append to node list to generate edge
            temp_list.append( nodoID )
            
            #generate the bolt 1d edge and take the id
            edgeID = MESH_TENUTA.AddEdge( temp_list )
            
            bolts_group.append(edgeID)

            #create the 1D bolt group in the layer mesh
            bolts_1d_list.append( MESH_TENUTA.CreateEmptyGroup( SMESH.EDGE, 'bolt1D_' + str(j) ) )
            nbAdd = bolts_1d_list[j].Add( [ edgeID ] )
            
            # get length value of the bolt
            measure = smesh.CreateMeasurements()
            length0 = round(measure.Length(bolts_1d_list[j]),5)
            
            # UPDATE XML FILE singleLoads with L0 (or creating new boltID singleLoad)
            
            # CASE 1 - we already have singleLoads entry in XML file
            try:
              singleLoads = mydoc.getElementsByTagName("singleLoad")
              
              # if there are no values raise exception
              if len(singleLoads) == 0 :
                raise ValueError('singleLoad undefined')
                
              err = 1
              for singleLoad in singleLoads:
                boltID = singleLoad.getElementsByTagName("boltID")[0].firstChild.data
                
                #check if we already have the boltID in the XML file
                if boltID == str(j):
                  print('Updating boltID '+str(j)+' in XML file')
                  
                  try:
                    # update the value if L0 exists in XML singleLoad
                    singleLoad.getElementsByTagName("L0")[0].firstChild.data = str(length0)
                    err = 0
                    
                  except:
                    # if L0 sub-element isn't inside singleLoad, we create one
                    L0 = mydoc.createElement("L0")
                    L0.appendChild(mydoc.createTextNode(str(length0)))
                    singleLoad.appendChild(L0) #add the element as singleLoad element child
                    err = 0
              
                  # check if diameter entry is listed, if not create one
                  try:
                    # check if diam exists in XML singleLoad
                    diam0 = float(singleLoad.getElementsByTagName("diam")[0].firstChild.data )
                    
                  except:
                    # if diam sub-element isn't inside singleLoad, we create one
                    diam0 = mydoc.createElement("diam")
                    diam0.appendChild(mydoc.createTextNode(str(0.006)))
                    singleLoad.appendChild(diam0)  #add the element as singleLoad element child
              
              if err == 1:
                raise ValueError('singleLoad undefined')
            
            # CASE 2 - we don't have a singleLoad entry in XML file so we create one'
            except:
              print('Creating new boltID '+str(j)+' in XML file')
              
              #if the singleLoad for the boltID is missing, we generate a new one
              singleLoad = mydoc.createElement("singleLoad")
              
              # generate element <multi>singleLoad</multi>
              multi = mydoc.createElement("multi")
              multi.appendChild(mydoc.createTextNode("singleLoad"))
              singleLoad.appendChild(multi) #add the element as singleLoad element child
              
              # generate element multipleID and give the value of the bolt+1
              multipleID = mydoc.createElement("multipleID")
              multipleID.appendChild(mydoc.createTextNode(str(j+1)))
              singleLoad.appendChild(multipleID) #add the element as singleLoad element child
              
              # generate element boltID and give the value of the bolt
              boltID = mydoc.createElement("boltID")
              boltID.appendChild(mydoc.createTextNode(str(j)))
              singleLoad.appendChild(boltID) #add the element as singleLoad element child
              
              # generate element L0 with the starting lenght value
              L0 = mydoc.createElement("L0")
              L0.appendChild(mydoc.createTextNode(str(length0)))
              singleLoad.appendChild(L0)  #add the element as singleLoad element child
              
              # generate element bolt diameter with a general value
              diam0 = mydoc.createElement("diam")
              diam0.appendChild(mydoc.createTextNode(str(0.006)))
              singleLoad.appendChild(diam0)  #add the element as singleLoad element child
              
              femSettings.appendChild(singleLoad)
            

            # export the updated value
            with open(work_path + '/FEM_input.xml', "w") as xml_file:
              xml_string = mydoc.toprettyxml()
              xml_string = os.linesep.join([s for s in xml_string.splitlines() if s.strip()]) # remove the weird newline issue
              #mydoc.writexml(xml_file)
              xml_file.write(xml_string)

        #create the 1D bolt overall group in the mesh - DISABLED NOW
        # boltsAll = MESH_TENUTA.CreateEmptyGroup( SMESH.EDGE, 'bolt1D_All') 
        # nbAdd = boltsAll.Add( bolts_group )  

    if salome.sg.hasDesktop():
      salome.sg.updateObjBrowser()
