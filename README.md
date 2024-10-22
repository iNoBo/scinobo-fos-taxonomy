# SciNoBo Field of Science Taxonomy

The taxonomy has 6 Levels (L1-L6). The levels from L1-L3 are static and stem from the OECD and ScienceMetrix taxonomy. The rest of the levels are algorithmically constructed utilizing publication-to-publication and venue-to-venue citation graphs as well as clustering and topic modelling algorithms. The resulting L5s are topics stemming from topic modelling. We utilize open-source LLMs and more specifically Llama3 to automatically assign a scientific name to each L5 topic. 

To view the FoS labels (L1-L3), please visit: [OpenAIRE FoS](https://explore.openaire.eu/fields-of-science). A snapshot of the taxonomy is visible below:

## Snapshot of the FoS taxonomy.
![image](docs/images/frma-08-1149834-g003.jpeg)


## Publications:
- [SCINOBO: a novel system classifying scholarly communication in a dynamically constructed hierarchical Field-of-Science taxonomy](https://www.frontiersin.org/articles/10.3389/frma.2023.1149834/full)
- [SciNoBo: A Hierarchical Multi-Label Classifier of Scientific Publications](https://dl.acm.org/doi/10.1145/3487553.3524677)

If you use this taxonomy, please cite the abovementioned publications.

## JSON structure:
The file containing the FoS taxonomy is a JSONL file and each line contains the following information:

- "level_1": The L1 of the FoS taxonomy
- "level_2": The L2 of the FoS taxonomy
- "level_3": The L3 of the FoS taxonomy
- "level_4": The L4 of the FoS taxonomy - This is a cluster of publications. The name stems from Wikipedia pages.
- "level_5": The L5 of the FoS taxonomy - This is a topic stemming from topic modelling in a cluster of publications. The L5 topic is the most frequent topic of the cluster. The rest of the topics are treated as L6. This is why a topic in L5 also occurs once in L6.
- "level_6": The L6 of the FoS taxonomy - This is a topic under L5, we treat each ngram in the topic description as a scientific kw and thus a L6.
- "level_4_id": A unique identifier for a L4
- "level_5_id": A unique identifier for a L5
- "level_5_name": The automatically assigned scientific name of the L5 topic, using open-source LLMs.

## Prompt for automatic topic labelling:

```#### Instruction: 
Your role is annotator. You provide labels based on information regarding a scientific topic.
The goal is to provide a label that accurately represents the scientific topic based on the provided topic description and information.
The label should be short and concise.
#### First Example Input: 
The scientific topic contains the following documents: 
Document 1: on the use of lateralization for lightweight and accurate methodology for eeg real time emotion estimation using gaussian-process classifier
Document 2: investigating the use of pretrained convolutional neural network on cross-subject and cross-dataset eeg emotion recognition
Document 3: cnn and lstm-based emotion charting using physiological signals
Document 4: the design of cnn architectures for optimal six basic emotion classification using multiple physiological signals
Document 5: end-to-end prediction of emotion from heartbeat data collected by a consumer fitness tracker
Document 6: analysis of the effect of dataset construction methodology on transferability of music emotion recognition models
Document 7: audio features for music emotion recognition: a survey
Document 8: emotion recognition using eye gaze based on shallow cnn with identity mapping
Document 9: multimodal emotion recognition using a hierarchical fusion convolutional neural network
Document 10: a novel signal to image transformation and feature level fusion for multimodal emotion recognition
The scientific topic is described by the following keywords: emotion ---- eeg ---- recognition ---- feature ---- emotion recognition ---- signal ---- base ---- propose ---- eeg signal ---- classification
The scientific topic belongs to the following Field of Science: artificial intelligence & image processing
The goal is to provide a label that accurately represents the scientific topic based on the provided topic description and information.
The label should be short and concise.
#### First Example Answer: 
Emotion Recognition
#### Second Example Input: 
The scientific topic contains the following documents: 
Document 1: using a supercapacitor to mitigate battery microcycles due to wind shear and tower shadow effects in wind-diesel microgrids
Document 2: hybrid energy storage control in a remote military microgrid with improved supercapacitor utilization and sensitivity analysis
Document 3: energy management and control for grid connected hybrid energy storage system under different operating modes
The scientific topic is described by the following keywords: storage ---- energy ---- battery ---- energy storage ---- frequency ---- power ---- control ---- propose ---- system ---- bess
The scientific topic belongs to the following Field of Science: energy
The goal is to provide a label that accurately represents the scientific topic based on the provided topic description and information.
The label should be short and concise.
#### Second Example Answer: 
Energy Storage System Control
#### Third Example Input: 
The scientific topic contains the following documents: 
Document 1: adaptive radiotherapy and the dosimetric impact of inter- and intrafractional motion on the planning target volume for prostate cancer patients
Document 2: delta radiomics for rectal cancer response prediction using low field magnetic resonance guided radiotherapy: an external validation
Document 3: comparison of helical tomotherapy with multi-field intensity-modulated radiotherapy treatment plans using simultaneous integrated boost in high-risk prostate cancer
Document 4: online adaptive mr-guided radiotherapy for rectal cancer; feasibility of the workflow on a 1.5t mr-linac: clinical implementation and initial experience
Document 5: three-dimensional surface and ultrasound imaging for daily igrt of prostate cancer
Document 6: hybrid tri-co-60 mri radiotherapy for locally advanced rectal cancer: an in silico evaluation
The scientific topic is described by the following keywords: prostate ---- dose ---- patient ---- radiotherapy ---- treatment ---- plan ---- cancer ---- prostate cancer ---- mm ---- image
The scientific topic belongs to the following Field of Science: oncology & carcinogenesis
The goal is to provide a label that accurately represents the scientific topic based on the provided topic description and information.
The label should be short and concise.
#### Third Example Answer: 
Prostate Cancer Radiotherapy Treatment
#### Input: 
The scientific topic is related to the following documents: 
Document [id]: [doc]
The scientific topic is described by the following topic description: [topic_desc]
The scientific topic is a subcategory of the following Field of Science: [fos]
#### Answer: 
```

## Examples:

```json
{
    "level_1": "engineering and technology", 
    "level_2": "electrical engineering, electronic engineering, information engineering", 
    "level_3": "artificial intelligence & image processing", 
    "level_4": "natural language processing/computational linguistics", 
    "level_4_id": "L4_artificial intelligence & image_9", 
    "level_5_id": "L4_artificial intelligence & image_9_24", 
    "level_5": "translation ---- machine ---- machine translation ---- language ---- neural ---- nmt ---- neural machine translation ---- neural machine ---- base ---- resource", 
    "level_6": "translation ---- machine ---- machine translation ---- language ---- neural ---- nmt ---- neural machine translation ---- neural machine ---- base ---- resource", 
    "level_5_name": "neural machine translation"
}
```

```json
{
    "level_1": "medical and health sciences", 
    "level_2": "clinical medicine", 
    "level_3": "oncology & carcinogenesis", 
    "level_4": "oncology/infectious causes of cancer", 
    "level_4_id": "L4_oncology & carcinogenesis_5", 
    "level_5_id": "L4_oncology & carcinogenesis_5_237", 
    "level_5": "tumor ---- malignant ---- gct ---- cell tumor ---- granular cell tumor ---- cell ---- granular cell ---- granular ---- case ---- patient", 
    "level_6": "tumor ---- malignant ---- gct ---- cell tumor ---- granular cell tumor ---- cell ---- granular cell ---- granular ---- case ---- patient", 
    "level_5_name": "granular cell tumor"
}
```
