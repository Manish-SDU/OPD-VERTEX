"""Shared structured demo transcripts for mock and seeded local flows."""

from __future__ import annotations


DEMO_CONSULTATION_TRANSCRIPTS: dict[int, str] = {
    4101: """Doctor: Good morning Ava, I am going to summarize the consultation so the chart is complete.
Chief Complaint: Sore throat, mild fever, and dry cough for two days.
History of Present Illness: The patient reports sore throat for two days with temperature up to 37.8 C, mild dry cough, painful swallowing, and no shortness of breath. Symptoms started gradually and are worse in the morning. She is able to drink fluids.
ROS General: Mild fever, reduced appetite, no chills.
ROS Respiratory: Mild dry cough, no dyspnea, no wheezing.
ROS Cardiovascular: No chest pain, no palpitations.
ROS Gastrointestinal: No nausea, no vomiting, no diarrhea.
ROS Neurological: No headache, no focal weakness.
ROS Genitourinary: No urinary symptoms.
ROS Musculoskeletal: Mild body aches.
ROS Other: No sick contacts confirmed.
Past Medical History: Mild seasonal allergies. No chronic cardiopulmonary disease.
Current Medications Mentioned: Cetirizine as needed for allergies.
Allergies: No known drug allergies.
Family History: Mother with allergic rhinitis.
Social Smoking: Never smoker.
Social Alcohol: Occasional social alcohol use.
Social Substance Use: Denies recreational drug use.
Social Occupation: Primary school teacher.
Vitals BP: 112/70 mmHg
Vitals HR: 84 bpm
Vitals Temp: 37.8 C
Vitals RR: 16/min
Vitals SpO2: 99% on room air
Vitals Weight: 64 kg
Vitals Height: 167 cm
Vitals BMI: 22.9
Examination Findings: Oropharynx mildly erythematous without exudate, cervical lymph nodes mildly tender, lungs clear to auscultation, patient well hydrated and in no acute distress.
Primary Diagnosis: Acute viral pharyngitis.
Differential Diagnoses: Streptococcal pharyngitis; Early upper respiratory tract infection.
Clinical Impression: Stable outpatient presentation without red flags. Conservative treatment is appropriate.
Medications: Paracetamol | 500 mg | oral | every 6 to 8 hours as needed | 3 days | take after food if stomach upset
Lab Tests Ordered: Rapid strep test if fever worsens or throat pain persists beyond 72 hours.
Plan Imaging: None.
Plan Referrals: None.
Follow Up: Re-evaluate in 3 to 5 days if symptoms do not improve.
Patient Instructions: Rest, hydrate well, use warm saline gargles, and avoid sharing utensils until symptoms improve.
Return Precautions: Seek urgent care for difficulty breathing; inability to swallow fluids; fever above 39 C; worsening throat swelling.
Clinical Notes Summary: Two-day uncomplicated sore throat syndrome most consistent with viral pharyngitis. Supportive outpatient management discussed.
Missing But Relevant Information: Exact exposure to known streptococcal infection not confirmed.
Doctor: Ava agrees with the plan and understands when to return.""",
    4102: """Doctor: Noah, I will document the visit in a structured way because the transcript was noisy.
Chief Complaint: Dizziness when standing up since last night.
History of Present Illness: The patient reports sudden dizziness starting last night, mainly when rising from bed or standing quickly. He describes lightheadedness rather than room spinning, with no fall, no syncope, and no chest pain. He drank little water yesterday and had several loose stools after a restaurant meal.
ROS General: Mild fatigue, no fever, no chills.
ROS Respiratory: No cough, no shortness of breath.
ROS Cardiovascular: No chest pain, no palpitations.
ROS Gastrointestinal: Two loose stools yesterday, no vomiting, mild nausea.
ROS Neurological: Lightheadedness, no focal weakness, no speech difficulty, no severe headache.
ROS Genitourinary: No dysuria, no urinary frequency.
ROS Musculoskeletal: No recent trauma.
ROS Other: Symptoms improve when sitting down.
Past Medical History: Hypertension treated with lisinopril.
Current Medications Mentioned: Lisinopril 10 mg once daily.
Allergies: No known drug allergies.
Family History: Father with hypertension and type 2 diabetes.
Social Smoking: Former smoker, quit 5 years ago.
Social Alcohol: Rare alcohol use.
Social Substance Use: Denies recreational drug use.
Social Occupation: Warehouse supervisor with long standing shifts.
Vitals BP: 102/66 mmHg standing, 118/74 mmHg sitting
Vitals HR: 96 bpm
Vitals Temp: 36.7 C
Vitals RR: 18/min
Vitals SpO2: 98% on room air
Vitals Weight: 86 kg
Vitals Height: 178 cm
Vitals BMI: 27.1
Examination Findings: Alert and oriented, mucous membranes mildly dry, heart regular rhythm, lungs clear, no focal neurological deficit, gait steady after hydration break.
Primary Diagnosis: Orthostatic dizziness likely related to mild dehydration.
Differential Diagnoses: Viral gastroenteritis with volume depletion; Medication-related hypotension; Benign positional vertigo.
Clinical Impression: No current evidence of acute cardiac or neurologic emergency, but close monitoring advised because of symptomatic postural blood pressure drop.
Medications: Oral rehydration salts | 1 sachet | oral | after each loose stool | 2 days | continue hydration; Meclizine | 25 mg | oral | every 8 hours as needed for dizziness | 3 days | avoid driving if drowsy
Lab Tests Ordered: Complete blood count; Basic metabolic panel.
Plan Imaging: None.
Plan Referrals: None.
Follow Up: Follow up within 48 hours or sooner if symptoms persist.
Patient Instructions: Increase oral fluids, stand up slowly, monitor home blood pressure twice daily, and temporarily avoid strenuous activity.
Return Precautions: Seek urgent care for fainting; chest pain; shortness of breath; persistent vomiting; new weakness or slurred speech.
Clinical Notes Summary: Postural dizziness after poor intake and loose stools, most consistent with mild dehydration and orthostatic symptoms.
Missing But Relevant Information: Exact stool frequency and oral intake volume were estimated rather than measured.
Doctor: Noah understands the plan and will check his blood pressure at home.""",
    4103: """Doctor: Mia, I will review the sinus symptoms and medication safety clearly in the note.
Chief Complaint: Facial pain, nasal congestion, and purulent nasal discharge for one week.
History of Present Illness: The patient reports one week of worsening sinus pressure over the cheeks, thick yellow nasal discharge, nasal blockage, post-nasal drip, and reduced smell. She denies shortness of breath and chest pain. She had a penicillin-associated rash in the past.
ROS General: Fatigue, no high fever.
ROS Respiratory: No dyspnea, mild cough from post-nasal drip.
ROS Cardiovascular: No chest pain, no palpitations.
ROS Gastrointestinal: No nausea, no vomiting.
ROS Neurological: Frontal headache related to sinus pressure, no focal deficit.
ROS Genitourinary: No urinary symptoms.
ROS Musculoskeletal: No neck stiffness.
ROS Other: Symptoms worse when bending forward.
Past Medical History: Recurrent sinus infections.
Current Medications Mentioned: Saline nasal spray as needed; Ibuprofen 200 mg occasionally.
Allergies: Penicillin allergy causing rash.
Family History: Sister with allergic rhinitis and asthma.
Social Smoking: Never smoker.
Social Alcohol: Occasional social alcohol use.
Social Substance Use: Denies recreational drug use.
Social Occupation: Graphic designer working from home.
Vitals BP: 116/72 mmHg
Vitals HR: 88 bpm
Vitals Temp: 37.4 C
Vitals RR: 16/min
Vitals SpO2: 99% on room air
Vitals Weight: 59 kg
Vitals Height: 164 cm
Vitals BMI: 21.9
Examination Findings: Maxillary sinus tenderness bilaterally, nasal mucosa congested, purulent discharge visible, throat mildly irritated from post-nasal drip, lungs clear.
Primary Diagnosis: Acute bacterial rhinosinusitis.
Differential Diagnoses: Viral upper respiratory infection; Allergic rhinitis flare.
Clinical Impression: Bacterial sinusitis is likely, but medication choice must account for documented penicillin allergy.
Medications: Doxycycline | 100 mg | oral | twice daily | 7 days | take with water and avoid lying down immediately; Saline nasal irrigation | 1 rinse | nasal | twice daily | 7 days | use sterile water
Lab Tests Ordered: None.
Plan Imaging: None.
Plan Referrals: ENT referral if recurrent episodes continue or symptoms fail to improve after treatment.
Follow Up: Review in 5 to 7 days if not improving.
Patient Instructions: Complete the antibiotic course, continue nasal saline irrigation, rest, and monitor for worsening fever or swelling.
Return Precautions: Seek urgent care for orbital swelling; severe headache; high fever; visual changes; confusion.
Clinical Notes Summary: Acute bacterial sinusitis with prior penicillin rash, therefore a non-penicillin regimen was selected and allergy was emphasized.
Missing But Relevant Information: Exact date and formulation of prior penicillin reaction not available.
Doctor: Mia repeated back the allergy plan and knows to avoid penicillin antibiotics.""",
    4104: """Doctor: Luca, I am documenting a broader fatigue workup so the report has all essential fields.
Chief Complaint: Persistent fatigue for several weeks.
History of Present Illness: The patient reports generalized fatigue for about six weeks, reduced exercise tolerance, intermittent lightheadedness, poor sleep, and difficulty concentrating during classes. No chest pain or shortness of breath. Appetite is slightly reduced with no significant weight loss.
ROS General: Fatigue, poor sleep, no fever, no night sweats.
ROS Respiratory: No cough, no dyspnea.
ROS Cardiovascular: No chest pain, no palpitations.
ROS Gastrointestinal: Mild reduced appetite, no abdominal pain, no vomiting, no diarrhea.
ROS Neurological: Intermittent lightheadedness, no syncope, no focal deficit.
ROS Genitourinary: No urinary symptoms.
ROS Musculoskeletal: Mild diffuse muscle tiredness after activity.
ROS Other: Increased academic stress noted.
Past Medical History: No major chronic illness reported.
Current Medications Mentioned: None.
Allergies: No known drug allergies.
Family History: Mother with hypothyroidism; maternal grandfather with iron deficiency anemia.
Social Smoking: Never smoker.
Social Alcohol: Rare alcohol use.
Social Substance Use: Denies recreational drug use.
Social Occupation: University student.
Vitals BP: 108/68 mmHg
Vitals HR: 82 bpm
Vitals Temp: 36.6 C
Vitals RR: 14/min
Vitals SpO2: 100% on room air
Vitals Weight: 70 kg
Vitals Height: 175 cm
Vitals BMI: 22.9
Examination Findings: Well appearing, conjunctiva slightly pale, thyroid not enlarged, heart regular rhythm, lungs clear, abdomen soft and non-tender, neurologic exam grossly normal.
Primary Diagnosis: Fatigue under evaluation, possible iron deficiency or sleep-related cause.
Differential Diagnoses: Iron deficiency anemia; Sleep deprivation; Thyroid dysfunction; Stress-related fatigue.
Clinical Impression: Stable outpatient evaluation appropriate, but laboratory workup is needed because symptoms are persistent and family history is relevant.
Medications: None.
Lab Tests Ordered: Complete blood count; Ferritin; Thyroid stimulating hormone; Vitamin B12.
Plan Imaging: None.
Plan Referrals: None at this stage.
Follow Up: Follow up after laboratory results within 1 week.
Patient Instructions: Maintain hydration, regular meals, sleep schedule, and bring a symptom diary to the next visit.
Return Precautions: Seek urgent care for chest pain; fainting; rapidly worsening weakness; shortness of breath.
Clinical Notes Summary: Several-week fatigue evaluation with broad differential and initial lab workup ordered.
Missing But Relevant Information: Baseline sleep duration and recent weight trend need more precise quantification.
Doctor: Luca agrees to complete the labs before the follow-up visit.""",
}
