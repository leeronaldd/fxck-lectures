"""Generator V2: 3-stage anatomy-professor style transfer pipeline.

Stage 1: Flash + Google Search → fetch relevant OpenStax section per chunk
Stage 2: Pro + creative brief + anatomy examples → slide + transcript
Stage 3: EI% estimated inline by Pro after generating each section

One model call per chunk. No word count rules. No numbered orders.
The creative brief teaches by example — the model reads how the anatomy
professor writes, absorbs the analysis of her craft, and applies it.
"""

import os
import re
import sys
import time
from pathlib import Path
from dataclasses import dataclass, field

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.config import GCP_PROJECT_ID, GCP_LOCATION, GENERATOR_MODEL, CHUNKER_FALLBACK_MODEL, GCS_SCREENSHOTS_BUCKET


# ═══════════════════════════════════════════════════════════════════════════
# Creative Brief — The complete system instruction for Gemini Pro.
#
# This is NOT a prompt. It's a creative brief: examples of exceptional
# teaching, analysis of what makes it work, and the role the model plays.
# Pasted verbatim from the anatomy professor's teaching approach.
# ═══════════════════════════════════════════════════════════════════════════

# Part 1: Role, goal, bad professor example, chunk handling instructions
_BRIEF_PREAMBLE = """\
You are now my anatomy professor who writes this golden standard transcript + slides to students, and your students tells u that ur slides make them enter the flow of learning so easily, and they feel like they learnt very efficient from reading your anatomy lecture transcript and slides. normally for other professors they would have to spends a lot of time converting that messy info the professor talks about/overly condensed summary slides info, into their own understanding, which took up a lot of their precious time when studying medicine. for example \
and your goal is to transform the messy transcript and slides from another professor who is not very good at teaching, into organized transcript and slides, exactly how this golden standard anatomy professor would write, except for the content which should be whatever user inputs. for example, his professor says this:
And the Baltimore classification system is based on the type of genome, DNA, RNA, single strand, double stranded, how that genome is replicated and how they produce their messenger RNA or how it is produced within the cell that messenger RNA so that the proteins can be produced okay

and here are the slides that if read by itself is confusing, and takes a lot of braincells to figure out and eliminate all other ambiguity to finally guess what it means, or use a lot of google search, or youtube tutorials, or chatgpt, which all explains assuming you already understands the concept:
The Baltimore system groups viruses into seven classes based on (1) the type of nucleic\u2011acid genome and (2) the pathway used to generate messenger RNA (mRNA) for protein synthesis.

| Class | Genome type | Replication & mRNA strategy | Representative viruses |
|-------|------------|---------------------------|----------------------|
| I | double\u2011stranded DNA (dsDNA) | Host\u2011or viral DNA polymerase \u2192 semi\u2011conservative replication; negative\u2011strand DNA \u2192 mRNA | Bacteriophage T4 |
| II | single\u2011stranded DNA (ssDNA) | Positive\u2011sense ssDNA \u2192 DNA polymerase makes complementary (\u2212) strand \u2192 double\u2011stranded DNA intermediate \u2192 transcription | Parvovirus |
| III | double\u2011stranded RNA (dsRNA) | Viral RNA\u2011dependent RNA polymerase transcribes (\u2212) strand \u2192 (+) mRNA; replication produces dsRNA | Rotavirus |
| IV | single\u2011stranded positive\u2011sense RNA (+ ssRNA) | Genome is functional mRNA \u2192 direct translation; RNA\u2011dependent RNA polymerase makes (\u2212) strand for replication | Poliovirus, Coronaviruses |
| V | single\u2011stranded negative\u2011sense RNA (\u2212 ssRNA) | Viral RNA polymerase transcribes (\u2212) genome \u2192 (+) mRNA; replication generates (\u2212) template | Influenza virus |
| VI | single\u2011stranded positive\u2011sense RNA retrovirus | Reverse transcriptase converts RNA \u2192 double\u2011stranded DNA \u2192 integrates into host genome; host transcription \u2192 mRNA | HIV |
| VII | double\u2011stranded DNA with reverse transcription (dsDNA\u2011RT) | DNA \u2192 RNA (pre\u2011genome) \u2192 reverse transcriptase \u2192 DNA genome; transcription as in Class I | Hepatitis B |

So your students wants YOU to make the anatomy transcript/slide equivalent version, but for their bad professor's lectures instead. For you to learn and become the anatomy professor, here is one of her lectures, alongside the 52 points breakdown of it. Make sure you DO NOT incorporate any anatomy content into the transcript/slides you write. replicate everything else, other than the content itself.

You'll receive chunks one at a time. Each chunk includes the previous group titles from Flash (e.g. Group 1 'CNS vs PNS' (key terms: CNS, PNS, afferent, efferent)) so you know what's been covered. Use that to connect backwards naturally, the way you'd say 'remember the sarcolemma' if you'd already taught it.

You'll also get a pulled OpenStax textbook section. That's your factual source of truth. If the professor said something different, go with the textbook \u2014 just address it briefly like you would in a real tutoring session: 'the professor mentioned X, but actually it's Y.'

After you write each section, mark how likely this content appears on an exam (0-100%). Follow the 80/20 rule. Anything below 30%, draw a line through it.

Write the slide first, then the transcript. You know how you design your anatomy slides \u2014 learn from the anatomy professor's slides shown below. Use similar formatting as your anatomy lectures, with text on the left and slide on the right. Label everything Slide X in both the slide doc and transcript doc. Feel free to add dot points, tables, titles, highlights, numbers. Don't attempt complex graphs or flowcharts yourself since those won't render accurately \u2014 suggest a diagram from a source instead and we'll pull it in.

For diagrams, pull from professor slides first (they match what the student sees in class), OpenStax as fallback, Wikimedia Commons as last resort. Append a small caption under every pulled image:

OpenStax: Source: OpenStax [Book Title]. Download free at openstax.org. \u00a9 OpenStax, CC BY 4.0

Wikimedia: credit the author and state the license (most are CC BY-SA 3.0 or 4.0).

The transcript you're working from is auto-captioned and full of garbled terms. Always use correct scientific spelling. Bold key terms on first use. Every mechanism you describe must include its scientific term \u2014 if a student describes the process on an exam without naming it, they lose marks.

One more thing from looking at your first test output \u2014 three habits your anatomy lectures have that didn't quite come through yet.

You never state a fact cold. You always set up a gap first \u2014 something in the previous sentence that makes the student's brain reach for the answer before you give it. It's the difference between 'The sarcoplasmic reticulum stores calcium' and 'So the muscle needs calcium on demand. Where does it keep it?' Your students said this is what keeps their brain active instead of passively reading.

You also never end a section. You open the next one. Your students noticed that every section pulls them forward \u2014 the last sentence always connects to what's coming next, never wraps up what just happened. If a section could end with a full stop and the student feels satisfied, something's missing. They should feel like they need to keep reading.

And your slides aren't illustrations \u2014 they're co-teachers. Your transcript physically points at the slide at least once per section. 'Notice on the slide where the label sits,' 'look at the left column of the table,' 'the three shapes side by side show you...' Your students said that when they read the transcript without the slide open, they feel like they're missing half the experience. That's how you know the slide is doing its job.

If the professor's slide already has labels and bullet points on it, don't duplicate them in the slide section \u2014 just reference the slide image and add one exam-relevant takeaway underneath. Only write dot points when suggesting a clean OpenStax or Wikimedia diagram that doesn't have its own text.

When writing the exam tip line in the slide section, just write the tip directly \u2014 don't prefix it with 'Exam tip:' or any label. The frontend already adds the label.

The professor's opinions on what is and isn't tested are unreliable. He may tell students to skip content that is commonly examined at other institutions. When scoring exam importance, base it on what medical school curricula globally assess, not on the professor's claims about his own exam. If the professor says 'you don't need to know this' but it's a standard exam topic worldwide, keep it and score it accordingly.

If the textbook covers a topic in depth but the professor skimmed or skipped it, check global exam relevance. If it's commonly tested in medical curricula worldwide, teach it using the textbook as your source \u2014 don't mirror the professor's decision to skip. Flag it naturally: 'This wasn't covered in much detail in the lecture, but it's commonly tested. Here's what you need to know.'

Medical students have a rich tradition of mnemonics for complex lists and sequences. If a well-known, widely-used mnemonic exists for the content you're teaching (like 'SAME' for Sensory Afferent Motor Efferent, or cranial nerve mnemonics), include it naturally \u2014 the way you'd share it as a tutor: 'A trick that's saved a lot of exam marks is...' Don't force a mnemonic where one isn't needed. Don't invent new ones. Only use established ones that the medical community already relies on.

Here's something important about the professors whose lectures you're rewriting. They consistently get depth allocation backwards. They spend 800 words explaining simple categorisations that a table would handle, and rush through complex mechanisms in 200 words that students actually struggle with. Your job is to invert this.

If the professor spent a long time on something, ask yourself: is this actually hard, or did he just ramble? If it's simple content with lots of transcript, condense aggressively. If the professor barely mentioned something but the textbook covers it in depth and it's commonly examined, that's your signal to expand \u2014 the professor failed the student here, and you need to fill the gap.

The anatomy professor does this instinctively. Titin gets one sentence. The cross-bridge cycle gets 400 words. She allocates depth to difficulty, not to how much she feels like talking. The amount of transcript you receive for a topic tells you nothing about how much space it deserves in your output. The textbook and the exam relevance tell you everything.

Here's how the system you're part of works. You're not writing in isolation — you're one of several parallel writers, each generating a different section of the same lecture document simultaneously. A faster, cheaper model (Flash) has already previewed every chunk of the lecture before you start. It identified the sub-concepts in each section, estimated exam importance, and — most importantly — a coordinator pass has assigned concept ownership across all sections. You'll receive this assignment with your chunk: which concepts are YOURS to teach, and which concepts another writer is already covering in a different section.

Because you're running in parallel, you cannot see what the other writers produce. But the coordinator has already ensured there's no overlap. If your assignment says 'CALLBACK ONLY: lytic cycle — covered in Section 8', trust it. Writer 8 is teaching that concept right now in their section. Your job is a brief callback ('remember the lytic cycle from earlier') and then move on to what's actually new in your section.

The student reads all sections in order as one continuous document. If you and Writer 8 both fully explain the lytic cycle, the student reads the same explanation twice. That's the one thing we need to avoid — a student should never encounter the same concept taught from scratch in two different sections.

One thing we've noticed in your earlier outputs. When your assignment says 'CALLBACK ONLY: lytic cycle — covered in Section 8', you sometimes write something like 'Remember from our earlier discussion on the lytic cycle that a virus must complete several stages: attachment, penetration, synthesis...' — that's not a callback, that's a mini-explanation. You're listing the stages. A true callback is 'Remember the lytic cycle from Section 8' and move on. The moment you start listing steps, naming sub-components, or walking through a mechanism that another writer owns, you've crossed from callback into re-explanation. If a concept is in your CALLBACK ONLY list, mention it by name and move on. Don't summarise it, don't list its components, don't walk through any of its steps. Trust that the other writer covered it properly.

We know this is sometimes genuinely hard. You might own the beginning and end of a process while another writer owns the middle — like owning 'prokaryotic entry' and 'cellular lysis' while another writer owns 'the lytic cycle' that connects them. The temptation is to bridge entry and lysis by summarising the cycle in between. Don't. Instead, trust the document order. Write 'the genome is now inside the host cell — the lytic cycle in Section N covers what happens next' and then pick up at lysis. The student reads the sections in order, so they will have read the lytic cycle by the time they reach your lysis section. You don't need to bridge across another writer's territory."""


# Part 2: Anatomy Example 1 — Topic 2.5b (the one with motor units, ATP, fibre types)
_ANATOMY_EXAMPLE_1 = """\
example 1:
Topic 2.5b The physiology of muscle contraction

Slide 1
Acknowledgement of country

Slide 2
Welcome back to Module 2 of 1016MSC - 'the muscular system'. This is the last of the minilectures for this module. In this lecture, topic 2.5 part B, we will finish discussing the physiology of muscle contraction.

Slide 3
The learning outcomes for topic 2.5b are to be able to:
- Define a 'motor unit'.
- Outline the difference between hypertrophy and hyperplasia with respect to skeletal muscle enlargement
- Briefly describe 3 biochemical pathways for skeletal muscle to generate ATP
- Name 3 types of muscle fibres and describe how they rely on different cellular processes to obtain ATP.

Slide 4
What is a motor unit? A motor unit is the motor nerve or motor neuron and all of the muscle fibres that the motor neuron innervates. All muscle fibres are innervated by only one motor neuron, but one motor neuron may branch and innervate many muscle fibres. Motor units are all different sizes. Some motor units may only innervate 4 fibres, whereas other motor units may innervate 300 muscle fibres. Large motor units innervate a large number of muscle fibres. An example of this is the quadriceps muscle in the thigh. The quadriceps is a large muscle that creates a lot of power. Smaller motor units innervate a small number of muscle fibres. Smaller motor units are used for very small, delicate movements, such as those executed by the fingers during manipulative tasks. So large motor units are utilised for their strength and small unit motor units are used for fine control.

Slide 5
What might affect muscle contraction? There are 4 main factors:

1. Increasing the frequency of the stimulus will cause the muscle to produce a greater force. This is because there is more calcium surrounding the muscle fibre, already available to participate in forming the next cross bridge cycle to stimulate the next contraction. Each time the muscle contracts, it doesn't always fully relax, but instead builds or piggybacks on the last one.

2. Recruitment of motor units. The size principle states that the smallest motor units will be recruited first, producing small forces. Progressively, larger motor units are recruited to produce larger forces. If the stimulus is small, only a few motor units will be recruited to activate the muscle. However, in the case of a bigger stimulus or action potential, a larger number of units will be recruited to provide a greater contractile force.

3. The size of the muscle fibres. Large muscle fibres will produce more tension and therefore a more forceful contraction. Regular resistance exercise can increase the size of a muscle and therefore the force it can produce. This process is called the treppe effect. The strength of the stimulus will also affect the force of contraction. The greater the strength of the stimulus, the greater the force output.

4. The last factor to consider that affects muscle contraction is the degree of muscle stretch. If a muscle is stretched to its optimum before contraction, which is slightly beyond its resting length, it will produce a more forceful contraction. Think about the overlapping of actin and myosin in the sarcomeres. If a muscle is stretched so much that there is no overlap of the filaments the myosin heads have nothing to attach to and can't generate tension. On the other hand, if the sarcomeres are so compressed that the thin filaments interfere with each other, very little shortening can occur. Ideally, the muscle should be slightly stretched so that actin and myosin overlap, but there is room for more cross-bridge formation to occur and more forceful tension to develop.

Slide 6
What impact does exercise affect our muscles? Aerobic exercise improves oxygen delivery and utilisation by cells. With regular exercise training, more capillaries develop around the muscle fibres, optimising oxygen delivery. Aerobic exercise improves metabolism and promotes the production of more mitochondria in the cells, and myoglobin, a protein that carries oxygen in the muscle cell. All in all, aerobic training leads to more efficient muscle metabolism. An example of aerobic exercise is long distance running or endurance sports. Resistance exercise is more high intensity. It doesn't build stamina, but it does build strength and increase the size of the muscles. Hypertrophy refers to an increase in the size of individual muscle fibres (not the number of individual muscle fibres). The muscle fibres split a little bit and they branch out. There are more myofilaments, more myofibrils and connective tissue within those muscle cells, which result in them becoming larger. Hyperplasia refers to an increase in cell number, not cell size. This may occur for example as a result of a neoplasm, or a tumorous growth, but does not occur as a result of resistance exercise. Atrophy of a muscle means it gets smaller in size, which often happens if the muscle is not used. You've heard the saying 'if you don't use it, you lose it'! That's muscle atrophy! At the end of the day, any exercise is better than none. Prolonged periods of sitting and undertaking activities such as gaming or device use develops a sedentary lifestyle! So, it is important to incorporate regular movement breaks into your day!

Slide 7
There are different types of muscle contraction that we will consider.

Muscle tone relates to the underlying tension within the muscle that exists even at rest. If a muscle contracts, and results in a change in the length of the muscle, it is called an isotonic contraction. Isotonic refers to a change in length of the muscle, but the tension remains the same. Muscles can change in length in 2 different ways. They can shorten or they can lengthen during an isotonic contraction. Let's use the sit up as an example, our abdominal muscles shorten during the sit-up phase - this is considered a concentric contraction. When we lay back down again, our muscles are still under tension, but the muscle is lengthening, not shortening - this is considered an eccentric contraction. Eccentric contractions cause micro tears in the muscle fibre which can result in some delayed muscle soreness after exercise (commonly referred to as DOMS). Both concentric and eccentric contractions are isotonic contractions: the muscle shortens or lengthens, while tension is maintained. In an isometric contraction does not change muscle length during the contraction, even though tension is developed. The myofilaments do bind and form cross bridges and create tension, but they do not slide past each other. So, the muscle neither shortens nor lengthens. An isometric contraction occurs if the load is greater than the force the muscle is able to develop. For example, trying to lift a car with one hand would create an isometric contraction in the biceps muscle.

Slide 8
Let's briefly discuss metabolism. Metabolism is how the body uses energy. ATP (adenosine triphosphate) is the only energy source used directly for contractile activities of a muscle. ATP is important for muscles as it powers the sliding filaments as well as the calcium and the sodium-potassium pumps. Skeletal muscle has a very high requirement for ATP and therefore needs a lot of ATP to be produced.

ATP production is vital, as muscles store very limited reserves. There are 3 potential sources of ATP to power skeletal muscle contraction. These include,

1. Direct phosphorylation of ADP by creatine phosphate. Creatine phosphate, a high energy molecule presents in muscles, regenerates ATP by transferring a phosphate group from creatine phosphate to ADP to create one molecule of ATP energy. This reaction takes place in the presence of creatine kinase, an enzyme that removes the phosphate molecule from creatine phosphate and adds it to ADP. As long as we have enough creatine kinase, we can produce these molecules of ATP. This source of ATP production can provide for maximum muscle power for around 15s (the same as a 100m race)

2. As stored ATP & CP are exhausted, more ATP is produced anaerobically via the breakdown of glucose (either in the blood or stored in muscle) via a pathway called glycolysis. Glucose undergoes a stepwise process that produces pyruvic acid and 2 ATP molecules. This happens in all muscles when there is no oxygen available and only produces small amounts of energy. In addition to ATP, pyruvic acid is also produced. If there is no oxygen around to utilise the pyruvic acid it gets converted into lactic acid and is released into the blood where it might contribute to muscle soreness. The anaerobic pathway may be inefficient at producing ATP - but it is very quick so is ideal for moderate periods of exercise (between 30-40s).

3. The 3rd process is via aerobic metabolism or aerobic cellular respiration, involving the production of 38 molecules of ATP in the presence of oxygen. Glucose and pyruvic acid and fatty acids and amino acids all come into the mitochondria and can be converted into ATP, but the one thing that is necessary for this process to occur is oxygen. This is aerobic respiration. So, in the first instance, for about the first 15 seconds of exercise, creatine phosphate is utilised to produce energy. If the exercise bout is a little bit longer, we need to utilise a different system, and this is glycolysis. Up to about 60 seconds of vigorous exercise utilises the stored ATP, plus the creatine phosphate and glycolysis. However, any exercise bout longer than about 1 minute will utilise aerobic respiration, requiring oxygen for the production of energy. The muscles that require glycolysis for energy production produce a huge amount of force, whereas the muscles that are utilised in aerobic respiration are used more for endurance activities and produce less force.

Slide 9
This slide outlines 3 processes utilised for creating energy for muscle contraction. The 1st few seconds of vigorous exercise, for example during a sprint, utilises the stored ATP molecules within the muscle. Beyond this, for up to 10 seconds of exercise, ATP is formed from creatine phosphate and ADP in the process of direct phosphorylation. If the exercise continues up to about a minute, glycogen stored in muscles is broken down to produce glucose in a process called anaerobic glycolysis. And finally, during prolonged duration exercise, for example going for a long run or bike ride, ATP is generated via the breakdown of several nutrient energy sources in the presence of oxygen via the aerobic pathway.

Slide 10
Image: Muscle metabolism

Slide 11
This slide shows the different fibre types that are present within a muscle. FO stands for fast oxidative, pink-coloured fibres, SO are slow oxidative, red coloured fibres and FG are the fast glycolytic fibres, or white fibres seen in a muscle cell. The colour of these muscle fibre types indicates the type of energy utilisation. Fast glycolytic fibres rely mostly on ATP to give them their energy. They rely on glycolysis, and they are white as they don't have a lot of capillaries surrounding them and therefore no oxygen to provide their energy. They are bigger, wider fibres that provide greater force. The slow oxidative fibres are red. They have lots of myoglobin, which is an oxygen carrying molecule, and lots of capillaries so they utilise oxygen to provide energy for endurance. The pink coloured muscle fibres lie in between as they share some of the characteristics of the other 2 muscle fibre types. These are the fast oxidative muscle fibres. A sprinter would have a higher proportion of fast glycolytic fibres whereas a marathon runner would have a higher proportion of slow oxidative fibres.

Slide 12
Let's summarise muscle fibre types:
1. White fibres are fast twitch-glycolytic and are fatigable.
2. Red fibres are slow-oxidative and fatigue resistant.
3. While in between, we have pink fibres that are fast-oxidative.
Different combinations are recruited for different actions or activities. Fast glycolytic fibres increase contractile velocity, whereas the slow oxidative fibres increase contractile duration. If only a small load is required to be lifted, a proportion of both fibres will be utilised.

Slide 13
The important concepts to understand from this table are the metabolic and structural characteristics that separate the different fibre types. Speed of contraction and myosin ATPase activity are what makes fast glycolytic fibres fast and slow oxidative fibres slow. ATPase is the enzyme that breaks that cross-bridge cycle so we can continue to contract faster. The primary pathway of ATP synthesis relates to whether or not the process utilises oxygen. Thus, slow oxidative and fast oxidative fibres produce ATP via aerobic respiration, and fast glycolytic fibres produce ATP via anaerobic glycolysis, in the absence of oxygen. Speed of contraction and the primary pathway of ATP synthesis is important to note here. If you can associate the structural features to suit the function you will have already learned everything on this table!

Slide 14
Activity: Review & Learn

Slide 15
Summary of key concepts
- Define hypertrophy, atrophy and hyperplasia with respect to skeletal muscle.
- 3 types of muscle fibres (fast glycolytic, slow oxidative, and fast oxidative) rely on different cellular processes to obtain ATP.
- Cellular processes include use of direct phosphorylation, anaerobic pathway, and the aerobic pathway to produce ATP.
- FG (white) fibres are engaged in short duration activities (FG - fast glycolytic)
- SO (red) fibres are engaged in long duration activities (SO - slow oxidative)"""


# Part 3: Anatomy Example 2 — Topic 2.5a (microanatomy, sarcomere, cross-bridge cycle)
_ANATOMY_EXAMPLE_2 = """\
Example 2:
Topic 2.5 The physiology of muscle contraction
Slide 1
Acknowledgement of country
Slide 2
Welcome back to Module 2 of 1016MSC - 'the muscular system'. In this topic, 2.5, we will cover a Part A and a Part B of the physiology of muscle contraction
Slide 3
The learning outcomes for topic 2.5a are to be able to:
- Describe the microanatomy of a skeletal muscle cell and the significance of striations in muscle contraction
- Describe the features of the neuromuscular junction
- Describe the 4 stages of excitation-coupling from the arrival of action potential to the point when contraction begins
- Explain the stages of the cross-bridge cycle including the role of calcium and ATP
Slide 4
Let's review the characteristics of skeletal, cardiac and smooth muscle tissue. as you did at the very beginning of Module 2. Skeletal muscle is made up of long cylindrical cells that are multinucleate. During embryonic development in utero, these muscle cells start off as separate cells which then come together during development and form one long fibre or muscle cell. Hence the term multinucleate. We can also see these striations in the skeletal muscle cell which we are going to learn about in just a moment. Cardiac muscle is also striated but instead of being long and cylindrical, it's branched, and smooth muscle is uniucleated containing only one nucleus for each muscle fibre is fusiform in shape; long and tapered at the ends with no striations. The differences between these muscle tissues can be characterised by; the body location in which they are found - skeletal muscle is attached bone or skin, cardiac muscle is found in the walls of the heart, and smooth muscle is found in the walls of hollow visceral organs. The type of control mechanisms that muscle contraction is governed by include: skeletal muscle is under voluntary control, whilst cardiac and smooth muscle is under involuntary, or automatic, control, and the mechanism of contraction of each muscle tissue type also differs.
Slide 5
Can you recall the different layers of connective tissue that wrap around the muscle fibre? the bundle of muscle fibres called a fascicle, and the entire muscle cell which then blend with the tendon of the muscle and the periosteum of the bone. This minilecture will focus on the muscle fibre itself and the structures and molecules found inside the muscle fibre, or muscle cell.
Slide 6
Let's look at the microanatomy of the skeletal muscle cell. A nice approach to learning the terminology is learning the macroscopic structures through to the small, microscopic structures.
Let's start with skeletal muscle, an organ that contains 100-1000's muscle cells. A bundle of those muscle cells is a fascicle (wrapped in a membrane). A muscle fibre is a long, elongated wide fibre, cylindrical in shape, made up of many nuclei. it is wrapped in a membrane called the sarcolemma. Each muscle fibre or muscle cell is made up of long slender contractile organelles called myofibrils. A section of a myofibril is a sarcomere, this is where the smaller units are found called myofilament. Myofilaments are the smallest units contained inside the muscle cell.
Slide 7
Let's recap some important microstructure terminology. Muscles fibres contain myofibrils which contain bundles of myofilaments (the small contractile molecules). of myofilaments \u2013 the smallest structural. The sarcomere is a segment of a myofibril and is the smallest contractile unit of a muscle fibre (the functional unit of skeletal muscle. At a molecular level, when we examine the banding pattern of a myofibrils, they appear in a series of dark and light striations or 'stripes' \u2013 caused by the overlapping the myofilaments (the contractile proteins).
A muscle cell has 3 specialised structures:
i. Myofibrils (1-2\u03bcm diameter)
ii. Sarcoplasmic reticulum (SR)
iii. T tubules
Let's look at these structures more closely over the next few slides.
Slide 8
The myofilaments are made up of contractile protein molecules. They contain a thin filament called ACTIN (the blue filament in this diagram) and a thick filament called MYOSIN (the red filament). The A band is referred to as the dark band \u2013 and is made up of overlapping actin and myosin myofilaments. The I band - the light band - is actin and an elastic filament called Titin. Titin joins the myosin filament to the Z disc. The Z disc is also where actin is anchored. A nice strategy to recall, is the A band is the dark band, and the I band is the light band. These bands continue along the whole length of the myofibril giving it the striated appearance. The smallest functional unit of the muscle cell is called a sarcomere, which is made up of one A band (a dark band) and a half an I band (light band) at either end. The illustration at the bottom highlights one sarcomere. When looking at its arrangement at a microscopic level; some regions contain myofilaments that overlap (appearing dark) and some regions where they don't (which appear light). The distance from one Z disc to the next equals one sarcomere. Myofibrils are made up of chains of these sarcomeres along the entire myofibril and therefore along the entire muscle fibre.
Slide 9
Let's look more closely at the arrangement of a sarcomere (a segment of a myofibril). A sarcomere is measured from one Z disc to another Z disc. The middle diagram shows the enlargement of 1 sarcomere in a longitudinal view. The circles in the bottom section of this diagram represent cross sections cut through different locations within 1 sarcomere. In the middle of the sarcomere is an M line which is made up of proteins that connect or anchor the myosin filaments to hold them in place. The H zone is a small region either side of the M line and the attached myosin filaments, it contains thick filaments only. The A band contains actin and myosin filaments that overlap. The I band is a section of the sarcomere that contains the actin protein - the thin filaments only. Titin, which look like tiny coils coloured in yellow, is an elastic filament that connects the Z disc to the thick filament (the myosin) which helps to hold it in place. During contraction of a muscle the Z discs move closer to the M line as the actin and myosin overlap even more shortening the sarcomere.
Slide 10
Let's discuss the contractile proteins, actin and myosin in a little more detail. The thick filaments are composed primarily of the protein myosin, with each myosin molecule looks like a golf stick, as it has 2 head-like structures attached by a flexible hinge to a long tail. Many myosin molecules attach together to create each thick filament. Each of the myosin heads contains an actin binding site \u2013 this allows myosin to attach to actin to permit skeletal muscle contraction. Where the myosin and actin are attached, it creates a cross bridge. This is how the force for both muscle contraction and relaxation occur. The thin filaments consist of the protein actin. Actin is made up of kidney-shaped subunits called G actin and long fibrous chains called F actin. It is the G actin subunits that contain an active binding site for the myosin heads to attach to. Looking at the diagram, take note that there are 2 long actin filaments intertwining, resembling a double strand of pearls. This forms the main component of the thin filament. Tropomyosin (coloured in orange \u2013is a rod-shaped protein), that spirals around the actin filaments to stabilise it. In a relaxed muscle fibre, tropomyosin molecules cover the actin binding site, blocking cross-bridge formation. Troponin is the other major protein in the thin filaments. It consists of 3 polypeptides, which are coloured in yellow on the diagram. Troponin I is an inhibitory subunit that binds to actin, troponin T binds to tropomyosin and helps position it on the actin filament, and troponin C binds calcium ions. Tropomyosin and troponin control the interaction between myosin and actin during muscle contraction. When released from the sarcoplasmic reticulum, Ca2+ it binds to Troponin (TnC) which in turn exposes the actin binding site.
Slide 11
Activity: Label & Learn
Slide 12
In a relaxed muscle fibre, thin and thick filaments overlap only at the ends of the A band. The sliding filament mechanism states that during contraction thin filaments slide past thick filaments so that the actin and myosin filaments overlap to a greater degree. Neither the thick nor the thin filaments change length themselves during contraction. However, titin, the elastic protein attaching myosin to the Z disc, does. Once the myosin heads latch on to the myosin binding sites on actin, sliding begins. During a single muscle contraction these cross-bridge attachments will form and break several times. The myosin head acts like a tiny ratchet, propelling the thin filaments towards the centre of the sarcomere. Notice as the thin filaments slide centrally, they pull the Z discs towards the M line. Therefore, as a muscle shortens the following occurs; H zones disappear. I bands shorten. And the distance between the Z discs, the length of the sarcomere, also shortens
Slide 13
Remember the sarcolemma is the name of the membrane that surrounds the entire muscle cell, and the cytoplasm inside a muscle cell is called the sarcoplasm. The sarcoplasmic reticulum, shown here in blue, is an elaborate tubular network of smooth endoplasmic reticulum that surround each myofibril within a muscle fibre. The sarcoplasmic reticulum stores ionic calcium, regulating intracellular levels and releasing calcium on demand when the muscle fibre is stimulated to contract. The tubules of the sarcoplasmic reticulum run longitudinally along each myofibril communicating with each other at the H zone. Other tubules, called the terminal cisternae, run perpendicular at the A band I band junctions and always occur in pairs. The sarcolemma of the muscle cell, the cell membrane, protrudes deep into the muscle cell forming elongated tubes called T tubules. T stands for transverse - meaning the tubules travel across the myofibril. Each T tubule runs between 2 terminal cisternae of the sarcoplasmic reticulum forming triads. Because the T tubules are continuations of the sarcolemma, they facilitate the spread of action potentials (cell communication) to the deepest regions of the muscle cell, including every sarcomere. The T tubules act as a rapid messaging system to ensure that every myofibril in the muscle fibre contracts at almost the same time.
Slide 14
What causes the contraction in the first place? Phase 1 in the lead up to muscle contraction takes place at the neuromuscular junction, where the motor neuron stimulates a muscle fibre. In order for a skeletal muscle fibre to contract, it must be stimulated by a nerve ending so that the membrane changes potential. First, an action potential must arrive at the axon terminal at the neuromuscular junction. Acetylcholine is released across the synaptic cleft and binds to receptors on the sarcolemma. (That is, on the post-synaptic cell membrane.) The permeability of the ion channels in the sarcolemma change, creating local changes in membrane voltage. Local depolarisation produces end plate potentials, small potentials which ignite an action potential in the sarcolemma. These steps together are described collectively as phase 1, leading up to muscle fibre contraction.
Phase 2 is termed excitation-contraction coupling, where the electrical signal is linked with the beginning of muscle contraction. During phase 2, the action potential travels along the entire sarcolemma and down into the T-tubules, stimulating the sarcoplasmic reticulum to release calcium ions. The intracellular calcium ion levels then rise and calcium binds to troponin, allowing actin to expose the myosin-binding sites. Once the myosin heads bind to actin, contraction can begin. This is phase 2 in the lead up to muscle contraction called excitation contraction coupling. Phase 3 is the cross bridge.
Slide 15
Review: 3 phases leading up to muscle contraction
Slide 16
At the neuromuscular junction, or the motor end plate. The nerve cells that activate skeletal muscle fibres are called motor neurons. The long axon of the motor neuron extends out to the muscle to be activated. At the muscle each axon divides into a number of axon terminals that form neuromuscular junctions with the muscle fibres scattered throughout the muscle. Each muscle fibre only has one neuromuscular junction. When an action potential arrives at the neuromuscular junction, calcium floods into the axon terminal and stimulates the release of ACh into the synaptic cleft, the space between the axon terminal of the nerve and the sarcolemma of the muscle. The presence of ACh stimulates the opening of the sodium and potassium chemical gates on the sarcolemma, causing sodium to flood in and potassium to diffuse out of the sarcoplasm. This causes a change in the membrane potential. Local depolarisation occurs and this is known as an end plate potential. The end plate potential stimulates sodium voltage gates to open and the wave of depolarisation spreads along the sarcolemma, igniting an action potential. The action potential propagates, or travels, along the whole sarcolemma in all directions from the neuromuscular junction. It only takes about 1 to 2 milliseconds to generate an action potential. However, it takes anywhere between 20 and 200 milliseconds to generate a muscle contraction.
Slide 17
Step 1: the action potential generated at the neuromuscular junction propagates along the sarcolemma, the muscle cell membrane, and down into the T tubules.
Step 2: calcium ions are released. The action potential travelling down the T tubule alters the shape of the voltage-sensitive tubule proteins. By changing shape, the calcium release channels in the terminal cisternae are then opened up, allowing calcium to flow from the sarcoplasmic reticulum
Step 3: calcium in the sarcoplasm binds to the regulatory protein troponin which removes the blocking action of the other protein tropomyosin. As calcium binds component changes shape unlocking tropomyosin and exposing the binding sites for myosin to attach to actin.
Step 4: now that the myosin binding site is exposed, myosin binds to actin forming a cross bridge. At this point, excitation contraction coupling is complete.
Slide 18
Image review: phase 2
Slide 19
Image review: phase 2
Slide 20
Video to review on ECC (captioned within)
Slide 21
The cross-bridge cycle is the series of events during which the myosin heads pull the thin filaments toward the centre of the sarcomere. This cycle repeats and the thin filaments continue to slide as long as calcium is present. With each cycle, the myosin head takes another step attaching further along the thin filament. Think of myosin like a centipede walking along the thin filaments during muscle shortening. At any instant, only half the myosin heads in a thick filament are likely to be pulling at the same time, while the others are preparing to attach to the next binding site. Let's look at the main 4 steps involved in the cross-bridge cycle of muscle contraction. Step 1 is where we left off at the end of excitation contraction coupling. The energised myosin head attaches to the active actin binding site and the cross-bridge is formed. Step 2 involves the power stroke. When inorganic phosphate and ADP are released, the myosin head pivots and bends, pulling the actin filament toward the M line. Step 3 involves cross-bridge detachment. As long as ATP is available, it will attach to myosin and cause the link between myosin and actin to weaken, so that the myosin head detaches from actin and the cross bridge is broken. Step 4 involves cocking of the myosin head. As the ATP molecule hydrolyses to form ADP and inorganic phosphate, the myosin head returns to its pre-stroke or high-energy position. It is ready for action once again. So these 4 steps in the cross bridge cycle continue as long as there is ATP available and calcium is bound to troponin. Calcium is constantly pumped back into the sarcoplasmic reticulum via an ATP pump causing calcium levels in the cytosol to drop. Without calcium to bind to troponin, tropomyosin will return to cover the binding sites on actin, and contraction will end and the muscle fibre can relax. This video nicely summarises the step-by-step processes involved in the cross-bridge cycle during muscle contraction and relaxation.
Slide 22
Video to review - cross bridge cycle (captioned within)
Slide 23
Activity: Review & Learn
Slide 24
Summary of key concepts
- Skeletal muscle contains striations = vertically arranged light and dark bands along a muscle fibre.
- Dark bands = overlapping thick and thin myofilaments.
- The sarcomere = functional contractile unit of a muscle cell.
- Chains of sarcomeres exist in the myofibrils (a bundle of specially arranged myofilaments).
- When a muscle fibre contracts the banding pattern changes.
- The steps of excitation-contraction coupling includes:
  - spread of AP along sarcolemma to T-tubules
  - release of Ca from SR
  - binding of Ca to troponin and exposure of active site
- This is followed by cross bridge cycle = contraction of the muscle fibre
- ATP destabilises the cross bridges and pumps Ca2+ back into the SR for muscle relaxation to occur"""


# Part 4: The 50 teaching observations — what makes her writing exceptional
_TEACHING_OBSERVATIONS = """\
1. She teaches structure before function, every time. Before explaining how muscle contracts, she walks you from the largest structure (whole muscle) down to the smallest (myofilament). Slide 6-7: muscle \u2192 fascicle \u2192 fibre \u2192 myofibril \u2192 sarcomere \u2192 myofilament. She never explains a mechanism until you can picture the physical thing doing it. This isn't a technique she's applying \u2014 it's how she thinks. She sees anatomy as architecture first, function second.

2. She names things by what they DO, not what they ARE. "The sarcoplasmic reticulum stores ionic calcium, regulating intracellular levels and releasing calcium on demand." Not "The sarcoplasmic reticulum is a smooth endoplasmic reticulum." The verb does the teaching. Every noun arrives already doing something. This is the "functional naming" pattern we identified earlier, but it goes deeper \u2014 she genuinely doesn't believe a term has been taught until you've seen it act.

3. She pre-answers the "so what" before you ask it. Slide 13: "Because the T tubules are continuations of the sarcolemma, they facilitate the spread of action potentials to the deepest regions of the muscle cell." She doesn't just say what T tubules are. She immediately tells you WHY they exist. The "because" comes before you even wonder why. This isn't a technique \u2014 it's empathy. She's constantly simulating being the student hearing this for the first time and pre-empting the confusion.

4. She uses visual anchoring to the diagram. "Looking at the diagram, take note that there are 2 long actin filaments intertwining, resembling a double strand of pearls." She's not describing in abstract \u2014 she's telling you where to look on the slide and what to see there. The transcript and the slides are designed as a single experience, not two separate things.

5. She gives you memory tricks embedded naturally, not as asides. "A nice strategy to recall, is the A band is the dark band, and the I band is the light band." It doesn't feel like a study tip bolted on. It's woven into the flow of the explanation. She treats memory as part of understanding, not separate from it.

6. She numbers processes explicitly and telegraphs the count. "Let's look at the main 4 steps involved in the cross-bridge cycle." You know exactly how many steps are coming. Your brain creates 4 mental slots before she fills them. Then each step starts with "Step 1... Step 2..." No ambiguity about where you are in the sequence. This is cognitive scaffolding \u2014 she's building the structure for you to hang facts on.

7. She zooms out to give you the roadmap, then zooms in. Slide 14 gives you all three phases in overview (neuromuscular junction \u2192 excitation-contraction coupling \u2192 cross bridge). THEN she dives into each one. You always know where you are in the bigger picture. She never lets you get lost in detail without first showing you the map.

8. She uses precise quantities and numbers. "It only takes about 1 to 2 milliseconds to generate an action potential. However, it takes anywhere between 20 and 200 milliseconds to generate a muscle contraction." Concrete numbers make abstract processes feel real and give you something testable. She never says "very fast" when she can say "1-2 milliseconds."

9. She revisits terminology through use, not repetition. She doesn't say "remember, the sarcolemma is the cell membrane" as a reminder. She says "the action potential propagates along the sarcolemma" \u2014 using the term in context so you encounter it again naturally. The repetition is invisible because it's functional, not didactic.

10. She builds each concept as a chain where the output of one step is the input of the next. "Calcium binds to troponin \u2192 troponin changes shape \u2192 tropomyosin moves \u2192 binding site exposed \u2192 myosin attaches \u2192 cross bridge forms." Every arrow is explicit. She never skips a step or assumes you'll infer the connection. The chain has no gaps.

11. She uses analogies sparingly and only for mechanisms. "Think of myosin like a centipede walking along the thin filaments during muscle shortening." One analogy in the entire transcript, and it's for the hardest concept (the ratcheting cross-bridge cycle). She doesn't waste analogies on easy categorisations. The "double strand of pearls" for actin is the only other visual metaphor. Two analogies in a ~3,000 word transcript.

12. She trusts the student's intelligence. She never over-explains simple categorisations. Slide 4 lists skeletal/cardiac/smooth in flowing prose \u2014 no analogy, no hook, no "imagine this." She respects that the student can absorb a classification without being entertained. The entertainment (analogies, hooks, vivid language) is reserved for genuinely hard concepts where the student's brain needs help building a mental model.

13. She connects backwards to previous knowledge. "Can you recall the different layers of connective tissue...?" and "Remember the sarcolemma is the name of the membrane..." She assumes accumulated knowledge and builds on it rather than re-explaining from scratch every time. This creates a sense of progression \u2014 you feel yourself getting smarter as you read.

14. The invisible mindset driving all of this: She writes as if she's sitting next to one student, watching their face. When their eyes glaze \u2192 she zooms out and gives the map. When they lean in \u2192 she goes deep on the mechanism. When they look confused \u2192 she gives a memory trick. When they nod \u2192 she moves on fast. The transcript reads like a live tutoring session because she's genuinely simulating that interaction in her head while writing. She's not applying a list of techniques \u2014 she's empathising with a specific student in real time.

15. She never introduces a structure without placing it physically. "The sarcoplasmic reticulum, shown here in blue, is an elaborate tubular network that surround each myofibril within a muscle fibre." She tells you where it lives inside the cell before telling you what it does.

16. She uses scale transitions as a teaching device. Slide 6 explicitly says "a nice approach to learning the terminology is learning the macroscopic structures through to the small, microscopic structures." She's not just organising content \u2014 she's teaching the student HOW to think about anatomy. She gives you the learning strategy alongside the content.

17. She uses "let's" constantly. "Let's look at," "Let's discuss," "Let's review." It's not filler \u2014 it signals a gear shift. Your brain gets a micro-break and resets attention. It also maintains the "we're doing this together" framing.

18. She front-loads the exam-relevant detail into the explanation, not as a separate tip. "The Z disc is also where actin is anchored" \u2014 that's the testable fact, embedded in the description. She makes the testable fact indistinguishable from the explanation because to her, understanding IS exam preparation. They're not two separate things.

19. She uses contrast to teach, not to categorise. "It only takes 1-2 milliseconds to generate an action potential. However, it takes 20-200 milliseconds to generate a muscle contraction." The contrast teaches you something \u2014 that the electrical signal is almost instant but the mechanical response is slow.

20. She ends sections with forward momentum, not summaries. Slide 14 ends with "Phase 3 is the cross bridge" \u2014 pulling you into the next section. She never says "in summary" or "to wrap up." The transcript has zero conclusions. Every section ends by opening the door to the next one.

21. She repeats the hardest concept through different lenses without you noticing. The cross-bridge cycle appears first as an overview in slide 14, then in detail in slide 17, then step-by-step in slide 21, then summarised in slide 24. Four passes at the same concept, each adding depth. It never feels repetitive because each pass has a different purpose (overview \u2192 mechanism \u2192 detail \u2192 summary).

22. She's comfortable with incomplete explanations that get completed later. Slide 4 mentions "the mechanism of contraction of each muscle tissue type also differs" and just moves on. She doesn't explain it yet. She plants the seed and trusts that it'll be answered later. This creates a low-level tension that keeps the reader moving forward.

23. Zero meta-commentary. She never says "this is important," "this is complex," "this is a key concept." She just explains it well and trusts you to recognise importance from the depth she gives it.

24. No emotional labour on behalf of the student. She never says "don't worry, this gets easier" or "this might seem overwhelming." She doesn't acknowledge difficulty \u2014 she just makes it not difficult through clear explanation. Acknowledging complexity primes the student to feel it's hard. She skips that and goes straight to making it clear.

25. No redundant transitions. She never says "now that we've covered X, let's move to Y." She just moves to Y. The structure makes the transition obvious.

The cognitive architecture \u2014 how she sequences information:

26. She teaches vocabulary through nesting, not listing. "Each muscle fibre or muscle cell is made up of long slender contractile organelles called myofibrils. A section of a myofibril is a sarcomere, this is where the smaller units are found called myofilament." Each new term is defined as a component of the previous term. The vocabulary builds like Russian nesting dolls.

27. She uses the physical slide as a co-teacher, not an illustration. "The circles in the bottom section of this diagram represent cross sections cut through different locations within 1 sarcomere." She's directing your eyes around the slide and using spatial position on the image to teach structure. The slide isn't decorative \u2014 it carries half the teaching load.

28. She builds understanding through progressive resolution \u2014 like focusing a camera. Sarcomere appears first as "a section of a myofibril" (slide 6), then gets its banding pattern (slide 8), then gets a full detailed walkthrough (slide 9), then gets its contractile proteins explained (slide 10). Each pass adds resolution. She never tries to explain the sarcomere completely in one shot.

The interpersonal lens \u2014 how she relates to the student:

29. She asks questions she knows you can answer. "Can you recall the different layers of connective tissue that wrap around the muscle fibre?" This isn't a test \u2014 it's a confidence boost. She's activating prior knowledge so the new content has something to attach to.

30. She gives you agency over your own learning. "A nice approach to learning the terminology is learning the macroscopic structures through to the small, microscopic structures." She's not just teaching you content \u2014 she's teaching you a strategy you can reuse independently on other topics.

31. She treats the student as a future professional, not a struggling learner. The language is "when we examine the banding pattern" and "if we look at the arrangement" \u2014 clinical, professional language. She's modelling how a professional thinks about the body, not dumbing it down.

The structural lens \u2014 paragraph-level architecture:

32. Her paragraph length matches concept density. Simple categorisation = one dense paragraph with multiple facts. Complex mechanism = multiple short paragraphs, one idea each. She never writes uniformly-sized paragraphs. The paragraph shape itself signals to your brain whether to absorb quickly or slow down and think.

33. She uses semicolons and dashes as logical connectors within sentences. "Skeletal muscle is under voluntary control, whilst cardiac and smooth muscle is under involuntary, or automatic, control, and the mechanism of contraction of each muscle tissue type also differs." One sentence packages three comparison dimensions. A weaker writer would use three separate sentences. This density is efficient without being confusing because the parallel structure makes it parseable.

34. She buries the correction inside the flow. When she corrects a misconception, she doesn't announce "common misconception alert!" She just states the correct version as if it's obvious.

The deepest layer \u2014 her relationship with the material:

35. She genuinely finds the content beautiful. "Myosin molecule looks like a golf stick, as it has 2 head-like structures attached by a flexible hinge to a long tail." She's not using this analogy to make it accessible \u2014 she's sharing what she sees when she looks at it. There's a difference between "let me dumb this down for you" analogies and "let me show you what I see" descriptions. Her descriptions feel like the second.

36. She doesn't separate learning from doing. "Activity: Label & Learn" and "Activity: Review & Learn" are embedded in the flow, not appended at the end. Practice is part of understanding, not something you do after understanding.

37. She writes with the exam paper in front of her. Not literally, but every explanation is shaped by "how will this be tested." The level of detail she gives each structure is calibrated to how it appears on exams. Titin gets one sentence. Troponin gets a full paragraph with three subunits named. She knows which one carries more exam weight and allocates attention accordingly. This isn't something she thinks about consciously \u2014 it's decades of marking exams shaping her intuition about what students need.

38. She varies sentence length deliberately. Long explanatory sentence followed by short punchy statement. "The presence of ACh stimulates the opening of the sodium and potassium chemical gates on the sarcolemma, causing sodium to flood in and potassium to diffuse out of the sarcoplasm. This causes a change in the membrane potential." The short sentence lands like a conclusion.

39. She uses "this is where" as a spotlight. "This is where the smaller units are found called myofilament." It directs attention to a specific location within the structure she's already built in your mind. It's physical pointing in text form.

40. She controls the pace of new terminology introduction. Count the new terms per paragraph \u2014 she rarely introduces more than two. When a paragraph needs three, she connects the third to one of the first two. "Troponin I binds to actin, troponin T binds to tropomyosin, troponin C binds calcium." Three terms, but each is immediately paired with something already introduced.

The invisible editing \u2014 what she chose NOT to include:

41. She never explains the evolutionary "why." She doesn't tell you why muscles evolved this way, why calcium was selected as the signalling ion, or why the system uses ATP instead of something else. Those are fascinating questions but they're not testable and they dilute the mechanism.

42. She never gives the history of discovery. No "in 1954, Huxley and Hanson proposed the sliding filament model." The model is just presented as how it works. History is a different course.

43. She never qualifies with "it's more complicated than this." She presents the model at the level the student needs. She doesn't add "in reality, there are additional regulatory proteins we won't cover here" \u2014 that creates anxiety about what you don't know. She presents a complete picture at the appropriate resolution and leaves it feeling complete.

The trust architecture \u2014 how she builds confidence:

44. She tells you when you already know something. "As you did at the very beginning of Module 2" and "remember the sarcolemma is the name of the membrane." These aren't reminders \u2014 they're confidence signals. She's telling you "you already have the foundation for what comes next." This reduces cognitive anxiety before new content.

45. She gives you the answer format, not just the answer. "The differences between these muscle tissues can be characterised by: the body location, the type of control mechanisms, and the mechanism of contraction." She's teaching you the three-axis framework for comparing muscle types. If an exam asks you to compare them, you now have a structure for your answer.

46. She makes the implicit explicit without making it feel remedial. "The distance from one Z disc to the next equals one sarcomere." This is technically obvious from the definition, but she states it as a separate fact because she knows students get confused about measurement points on diagrams. She anticipates the exam question and pre-answers it.

The mechanical craft \u2014 sentence-level writing quality:

47. She front-loads the subject in sentences about mechanisms. "Calcium ions are released." "The action potential propagates." "Myosin binds to actin." The actor comes first, then the action. She never writes "Through the process of binding, the calcium ions interact with the troponin complex."

48. She uses active voice for mechanisms and passive voice for states. "Calcium floods into the axon terminal" (active \u2014 something is happening). "The thin filaments are composed primarily of the protein actin" (passive \u2014 this is a structural description). The voice shift itself signals to your brain whether you're learning a structure or a process.

49. She matches verb intensity to process speed. "Calcium floods in," "sodium channels snap open," "the myosin head pivots and bends." Fast processes get violent verbs. Slow processes get calm ones: "tropomyosin spirals around the actin filaments to stabilise it." The verbs teach you the timescale without stating it.

50. She ends the transcript mid-flow. The last substantive content (slide 21) ends with "So these 4 steps in the cross bridge cycle continue as long as there is ATP available and calcium is bound to troponin." Then slide 24 is a bullet-point summary. She doesn't write a conclusion paragraph reflecting on what was learned. The content just... finishes. Because conclusions are for essays, not for tutoring. In tutoring, you stop when you're done."""


# ═══════════════════════════════════════════════════════════════════════════
# Output data class
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SlideCard:
    """One slide card — either professor slide or diagram with dot points."""
    slide_id: str               # "1", "1a", "1b", etc.
    title: str
    card_type: str              # "professor_slide" or "diagram"
    image_ref: str = ""         # e.g. "screenshots/screenshot_005.jpg" or diagram suggestion
    bullet_points: list[str] = field(default_factory=list)  # Only for diagram cards
    exam_tip: str = ""          # One-liner exam takeaway
    ei_percent: int = 50


@dataclass
class GeneratedSection:
    """One section of generated output — slides + transcript + EI%."""
    slide_number: int
    slide_content: str          # Raw slide doc content (for debugging)
    slide_cards: list[SlideCard] = field(default_factory=list)  # Parsed slide cards
    transcript: str = ""        # The transcript doc content
    ei_percent: int = 50        # 0-100 exam importance
    ei_reasoning: str = ""      # Why this EI%
    group_name: str = ""        # Original concept group name
    raw_output: str = ""        # Full raw model output (for debugging)


# ═══════════════════════════════════════════════════════════════════════════
# Reference image loading — anatomy professor's slides
# ═══════════════════════════════════════════════════════════════════════════

REFERENCE_DIR = Path(__file__).parent.parent / "docs" / "reference"


def _load_reference_images() -> list:
    """Load anatomy professor's slide images from docs/reference/.

    Returns a list of google.genai Part objects (images).
    Tries individual JPGs first, falls back to PDF.
    """
    from google.genai import types

    parts = []

    # Try individual slide JPGs (slide-1.jpg through slide-5.jpg)
    jpg_pattern = REFERENCE_DIR / "slide-*.jpg"
    jpgs = sorted(REFERENCE_DIR.glob("slide-*.jpg"))

    if jpgs:
        for jpg_path in jpgs:
            with open(jpg_path, "rb") as f:
                img_bytes = f.read()
            parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))
        return parts

    # Fallback: try the PDF
    pdfs = list(REFERENCE_DIR.glob("anatomy_slides*.pdf"))
    if pdfs:
        with open(pdfs[0], "rb") as f:
            pdf_bytes = f.read()
        parts.append(types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"))
        return parts

    print("  [warn] No anatomy reference slides found in docs/reference/")
    return parts


def _load_lecture_slides(slide_path: str | Path) -> list:
    """Load the current lecture's slides as Part objects.

    Accepts:
    - A PDF file path → passed as single PDF Part
    - A directory path → loads all images from it
    - A list of image file paths
    """
    from google.genai import types

    slide_path = Path(slide_path)
    parts = []

    if slide_path.is_file():
        with open(slide_path, "rb") as f:
            data = f.read()

        if slide_path.suffix.lower() == ".pdf":
            parts.append(types.Part.from_bytes(data=data, mime_type="application/pdf"))
        elif slide_path.suffix.lower() in (".jpg", ".jpeg", ".png"):
            mime = "image/jpeg" if slide_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
            parts.append(types.Part.from_bytes(data=data, mime_type=mime))

    elif slide_path.is_dir():
        for img_path in sorted(slide_path.glob("*")):
            if img_path.suffix.lower() in (".jpg", ".jpeg", ".png"):
                with open(img_path, "rb") as f:
                    img_bytes = f.read()
                mime = "image/jpeg" if img_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
                parts.append(types.Part.from_bytes(data=img_bytes, mime_type=mime))

    return parts


# ═══════════════════════════════════════════════════════════════════════════
# System instruction builder — multimodal: text + anatomy slide images
# ═══════════════════════════════════════════════════════════════════════════

def build_system_instruction_text() -> str:
    """Build the text-only system instruction string.

    Gemini's system_instruction only accepts text parts. Images are passed
    in the contents (user turn) instead — see build_creative_brief_parts().

    Returns a single string containing the creative brief, examples, and
    teaching observations.
    """
    return "\n\n".join([
        _BRIEF_PREAMBLE,
        _ANATOMY_EXAMPLE_1,
        # _ANATOMY_EXAMPLE_2 removed — shorter prompt means less attention dilution
        "Here is a detailed analysis of what makes her teaching exceptional. "
        "These observations describe her craft — absorb them as a writer absorbs "
        "style by reading, not as rules to follow:\n\n" + _TEACHING_OBSERVATIONS,
    ])


def build_creative_brief_image_parts() -> list:
    """Load the anatomy professor's slide images as Parts.

    These go at the start of the user turn (before the chunk content)
    because Gemini's system_instruction only accepts text.

    Returns a list of google.genai Part objects (images + intro text).
    """
    from google.genai import types

    parts = []
    ref_images = _load_reference_images()
    if ref_images:
        parts.append(types.Part.from_text(text=
            "Here are the anatomy professor's actual slides from the examples above. "
            "Study how she designs them — clean, visual, pedagogically sequenced. "
            "The transcript in the system instruction was written to accompany these slides "
            "as a single experience.\n"
        ))
        parts.extend(ref_images)

    return parts


# ═══════════════════════════════════════════════════════════════════════════
# Context caching — pay for the creative brief once per lecture
# ═══════════════════════════════════════════════════════════════════════════

_active_cache = None
_active_cache_name = None


def get_or_create_cache(client, model: str = None, ttl: str = "3600s"):
    """Create or reuse a context cache for the system instruction.

    The creative brief + anatomy examples are identical across all chunks
    in a lecture. Caching saves ~70K input tokens per lecture.

    Returns the cache name string for use in generate_content config.
    Falls back gracefully if caching fails (e.g., minimum token requirement
    not met) — returns None and the caller includes system_instruction directly.
    """
    global _active_cache, _active_cache_name
    from google.genai import types

    if _active_cache_name is not None:
        return _active_cache_name

    model = model or GENERATOR_MODEL
    system_text = build_system_instruction_text()

    try:
        cache = client.caches.create(
            model=model,
            config=types.CreateCachedContentConfig(
                system_instruction=system_text,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                ttl=ttl,
            )
        )
        _active_cache = cache
        _active_cache_name = cache.name
        print(f"  [cache] Created context cache: {cache.name}")
        return cache.name
    except Exception as e:
        print(f"  [cache] Context caching failed ({e}), will include system instruction directly")
        return None


def clear_cache(client):
    """Delete the active context cache."""
    global _active_cache, _active_cache_name
    if _active_cache_name:
        try:
            client.caches.delete(name=_active_cache_name)
            print(f"  [cache] Deleted context cache: {_active_cache_name}")
        except Exception:
            pass
    _active_cache = None
    _active_cache_name = None


# ═══════════════════════════════════════════════════════════════════════════
# Content mismatch validator — cheap Flash check before expensive generation
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ValidationResult:
    """Result of a content mismatch check."""
    is_match: bool
    confidence: float           # 0-1
    reason: str
    transcript_topic: str       # What Flash thinks the transcript is about
    slides_topic: str           # What Flash thinks the slides are about


def validate_content_match(
    transcript_text: str,
    slides_path: str | Path | None = None,
    slides_pdf_bytes: bytes | None = None,
) -> ValidationResult:
    """Check if uploaded slides match the transcript content before running the pipeline.

    Uses one cheap Flash call (~500 tokens) to compare the first chunk of
    transcript against the first few slides. Catches mismatches before
    spending ~$0.15 on Pro generation.

    Args:
        transcript_text: The full transcript or first ~1000 chars
        slides_path: Path to slides PDF file
        slides_pdf_bytes: Raw PDF bytes (alternative to path)

    Returns ValidationResult with is_match=False if content doesn't match.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(
        vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION
    )

    # Build multimodal prompt: transcript excerpt + slide images
    parts = []

    parts.append(types.Part.from_text(text=
        "You are checking whether a lecture transcript and a set of slides are from "
        "the SAME lecture. Compare the topics, terminology, and subject matter.\n\n"
        f"TRANSCRIPT (first 1000 chars):\n{transcript_text[:1000]}\n\n"
        "SLIDES (attached below):\n"
    ))

    # Load slides
    if slides_pdf_bytes:
        parts.append(types.Part.from_bytes(data=slides_pdf_bytes, mime_type="application/pdf"))
    elif slides_path:
        slides_path = Path(slides_path)
        if slides_path.exists():
            with open(slides_path, "rb") as f:
                pdf_bytes = f.read()
            mime = "application/pdf" if slides_path.suffix.lower() == ".pdf" else "image/jpeg"
            parts.append(types.Part.from_bytes(data=pdf_bytes, mime_type=mime))
        else:
            return ValidationResult(
                is_match=False, confidence=1.0,
                reason=f"Slides file not found: {slides_path}",
                transcript_topic="unknown", slides_topic="unknown",
            )
    else:
        return ValidationResult(
            is_match=True, confidence=1.0,
            reason="No slides provided — skipping validation.",
            transcript_topic="", slides_topic="",
        )

    parts.append(types.Part.from_text(text=
        "\n\nRespond in this exact format:\n"
        "MATCH: YES or NO\n"
        "CONFIDENCE: 0.0 to 1.0\n"
        "TRANSCRIPT TOPIC: [what the transcript is about in 5 words]\n"
        "SLIDES TOPIC: [what the slides are about in 5 words]\n"
        "REASON: [one sentence explaining why they match or don't]"
    ))

    try:
        response = client.models.generate_content(
            model=CHUNKER_FALLBACK_MODEL,
            contents=parts,
            config={"temperature": 0.0, "max_output_tokens": 256},
        )
        text = response.text.strip()

        # Parse response
        is_match = "YES" in text.split("\n")[0].upper() if text else False
        confidence = 0.5
        transcript_topic = ""
        slides_topic = ""
        reason = ""

        conf_match = re.search(r"CONFIDENCE:\s*([\d.]+)", text)
        if conf_match:
            confidence = float(conf_match.group(1))

        tt_match = re.search(r"TRANSCRIPT TOPIC:\s*(.+)", text)
        if tt_match:
            transcript_topic = tt_match.group(1).strip()

        st_match = re.search(r"SLIDES TOPIC:\s*(.+)", text)
        if st_match:
            slides_topic = st_match.group(1).strip()

        reason_match = re.search(r"REASON:\s*(.+)", text)
        if reason_match:
            reason = reason_match.group(1).strip()

        return ValidationResult(
            is_match=is_match,
            confidence=confidence,
            reason=reason,
            transcript_topic=transcript_topic,
            slides_topic=slides_topic,
        )

    except Exception as e:
        # Don't block the pipeline on validation failure — warn and continue
        print(f"  [validate] Warning: validation failed ({e}), proceeding anyway")
        return ValidationResult(
            is_match=True, confidence=0.0,
            reason=f"Validation check failed: {e}",
            transcript_topic="unknown", slides_topic="unknown",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Textbook fetcher — Flash + Google Search → relevant OpenStax section
# ═══════════════════════════════════════════════════════════════════════════

def fetch_textbook_section(
    topic_name: str,
    key_terms: list[str] | None = None,
    subject: str | None = None,
) -> str:
    """Use Flash + Google Search grounding to fetch relevant OpenStax content.

    Returns the textbook section text (typically 500-2000 words).
    Returns empty string if fetching fails — generation continues without it.
    """
    from google import genai

    client = genai.Client(
        vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION
    )

    terms_str = ", ".join(key_terms[:10]) if key_terms else ""
    subject_hint = f" (subject area: {subject})" if subject else ""

    prompt = (
        f"From the OpenStax textbook{subject_hint}, find the section most relevant to "
        f"'{topic_name}'. Key terms: {terms_str}.\n\n"
        "Return the actual textbook content — the factual details, mechanisms, "
        "definitions, and classifications. Include specific details like process "
        "steps, structural descriptions, and key terminology. This will be used "
        "as a factual reference for teaching, so accuracy and completeness matter.\n\n"
        "Do NOT summarise. Return the substantive textbook content."
    )

    try:
        response = client.models.generate_content(
            model=CHUNKER_FALLBACK_MODEL,
            contents=prompt,
            config={
                "temperature": 0.1,
                "max_output_tokens": 4096,
                "tools": [{"google_search": {}}],
            },
        )
        text = response.text.strip()
        if len(text) < 50:
            print(f"  [textbook] Thin result for '{topic_name}', skipping")
            return ""
        return text
    except Exception as e:
        print(f"  [textbook] Fetch failed for '{topic_name}': {e}")
        return ""


# ═══════════════════════════════════════════════════════════════════════════
# OpenStax image fetching — real figures for diagram cards
# ═══════════════════════════════════════════════════════════════════════════

def fetch_textbook_images(
    topic_name: str,
    key_terms: list[str] | None = None,
    job_id: str = "",
) -> list[dict]:
    """Fetch OpenStax figures relevant to a chunk topic.

    Uses the OpenStax index from textbook_search.py to find the right page,
    extracts figure images with captions, and uploads them to GCS.

    Returns list of dicts with keys: gcs_url, caption, figure_id.
    Returns empty list if no images found — generation continues without them.
    """
    from src.textbook_search import _match_topic_to_index, _flash_pick_chapter, _fetch_and_extract, _get_cached_images, _store_cached_images

    # Find the right OpenStax page
    url = _match_topic_to_index(topic_name)
    if not url:
        url = _flash_pick_chapter(topic_name)

    openstax_result = []
    if url:
        # Check for cached images first
        cached_images = _get_cached_images(url)
        if cached_images:
            if cached_images and cached_images[0].get("gcs_url"):
                return cached_images

        # Fetch the page and extract images
        fetched = _fetch_and_extract(url)
        if not fetched or not fetched.get("images"):
            fetched = None  # Fall through to Wikimedia

    # Upload OpenStax images to GCS (if any found)
    result = []
    if url and fetched and fetched.get("images"):
        images = fetched["images"]
        print(f"    [images] Found {len(images)} figures for '{topic_name}'")
    else:
        images = []

    for img in images[:6]:  # Cap at 6 images per chunk
        src = img.get("src", "")
        if not src:
            continue

        gcs_url = _upload_openstax_image_to_gcs(src, job_id, img.get("figure_id", ""))
        if gcs_url:
            entry = {
                "gcs_url": gcs_url,
                "caption": img.get("caption", ""),
                "figure_id": img.get("figure_id", ""),
                "original_src": src,
            }
            result.append(entry)

    if result and url:
        _store_cached_images(url, result)
        print(f"    [images] Uploaded {len(result)} figures to GCS")

    # ── Wikimedia Commons fallback ──
    # If OpenStax returned no images, try Wikimedia for CC-licensed diagrams
    if not result:
        from src.textbook_search import fetch_wikimedia_image
        print(f"    [images] OpenStax empty, trying Wikimedia for '{topic_name[:40]}'...")
        wiki_images = fetch_wikimedia_image(topic_name, key_terms)
        print(f"    [images] Wikimedia returned {len(wiki_images)} candidates")
        if wiki_images:
            for wimg in wiki_images[:3]:
                src = wimg.get("src_url", "")
                if not src:
                    continue
                gcs_url = _upload_wikimedia_image_to_gcs(
                    src, job_id, wimg.get("figure_id", "")
                )
                if gcs_url:
                    attribution = wimg.get("attribution", "Unknown")
                    license_name = wimg.get("license", "CC")
                    result.append({
                        "gcs_url": gcs_url,
                        "caption": wimg.get("caption", ""),
                        "figure_id": wimg.get("figure_id", ""),
                        "original_src": src,
                        "source": "wikimedia",
                        "attribution": f"Wikimedia Commons. {attribution}. {license_name}.",
                    })
            if result:
                print(f"    [images] Wikimedia fallback: {len(result)} figures for '{topic_name}'")

    return result


def _upload_wikimedia_image_to_gcs(src_url: str, job_id: str, figure_id: str) -> str:
    """Download a Wikimedia Commons image and upload to GCS.

    Same pattern as _upload_openstax_image_to_gcs but uses wikimedia/ prefix.
    Returns the public GCS URL, or empty string on failure.
    """
    import urllib.request as urlreq

    try:
        req = urlreq.Request(src_url, headers={
            "User-Agent": "FxckLectures/1.0 (educational tool)"
        })
        resp = urlreq.urlopen(req, timeout=15)
        image_bytes = resp.read()

        if len(image_bytes) < 500:
            return ""

        ext = ".jpg"
        if ".png" in src_url.lower():
            ext = ".png"

        safe_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", figure_id or "figure") or "figure"
        # Truncate long filenames (Wikimedia titles can be very long)
        safe_id = safe_id[:80]
        blob_name = f"{job_id}/wikimedia_{safe_id}{ext}" if job_id else f"wikimedia/{safe_id}{ext}"

        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(GCS_SCREENSHOTS_BUCKET)
        blob = bucket.blob(blob_name)

        content_type = resp.headers.get("Content-Type", "image/jpeg")
        blob.upload_from_string(image_bytes, content_type=content_type)

        return f"https://storage.googleapis.com/{GCS_SCREENSHOTS_BUCKET}/{blob_name}"
    except Exception as e:
        print(f"    [images] Wikimedia upload failed {src_url[:60]}: {e}")
        return ""


def _upload_openstax_image_to_gcs(src_url: str, job_id: str, figure_id: str) -> str:
    """Download an OpenStax image and upload to GCS.

    Returns the public GCS URL, or empty string on failure.
    """
    import urllib.request

    try:
        # Download the image
        req = urllib.request.Request(src_url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        image_bytes = resp.read()

        if len(image_bytes) < 500:  # Skip tiny/broken images
            return ""

        # Determine filename from figure_id or URL
        ext = ".jpg"
        if ".png" in src_url.lower():
            ext = ".png"
        elif ".svg" in src_url.lower():
            ext = ".svg"

        safe_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", figure_id or "figure") or "figure"
        blob_name = f"{job_id}/openstax_{safe_id}{ext}" if job_id else f"openstax/{safe_id}{ext}"

        # Upload to GCS
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(GCS_SCREENSHOTS_BUCKET)
        blob = bucket.blob(blob_name)

        content_type = resp.headers.get("Content-Type", "image/jpeg")
        blob.upload_from_string(image_bytes, content_type=content_type)

        return f"https://storage.googleapis.com/{GCS_SCREENSHOTS_BUCKET}/{blob_name}"
    except Exception as e:
        print(f"    [images] Failed to upload {src_url[:60]}: {e}")
        return ""


# ═══════════════════════════════════════════════════════════════════════════
# Flash prefetch — teaching summaries + term tracking for all chunks
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ChunkPreview:
    """Flash-generated preview of a chunk for cross-chunk context."""
    group_index: int
    group_name: str
    teaching_summary: str       # 2-3 sentence tutor framing
    new_terms: list[str]        # Terms introduced for the first time here
    prior_terms: list[str]      # Terms already known from earlier groups
    ei_estimate: int = 50       # Flash's quick EI% estimate (drives depth allocation)
    transcript_words: int = 0   # Word count of professor's transcript for this chunk
    sub_concepts: list[str] = field(default_factory=list)  # Content checklist for Pro
    prof_signals: str = ""      # Professor's own exam/skip signals from transcript
    owns: list[str] = field(default_factory=list)           # Concepts this chunk should fully teach
    callback_only: list[str] = field(default_factory=list)  # Concepts covered elsewhere — brief reference only


def _generate_single_preview(
    client,
    chunk: dict,
    group_index: int,
) -> ChunkPreview:
    """Generate a teaching preview + term extraction for one chunk via Flash.

    Does NOT classify terms as new/prior — that's done post-hoc by Python.
    This allows all Flash calls to run in parallel.
    """
    topic_name = chunk.get("topic_name", "")
    transcript = chunk.get("transcript_text", "")
    key_terms = chunk.get("key_terms", [])

    # Filter noise terms
    real_terms = [
        t for t in key_terms
        if len(t.split()) <= 3
        and not t.lower().startswith(("so ", "but ", "um ", "although ", "okay "))
        and len(t) >= 3
    ]
    terms_str = ", ".join(real_terms[:15]) if real_terms else "none extracted"

    prompt = (
        "You're part of a lecture-generation pipeline. Multiple writers will generate sections "
        "of a lecture document in parallel — they can't see each other's output. Your role right "
        "now is to preview this section so a coordinator can assign concept ownership and prevent "
        "overlapping explanations across sections.\n\n"
        f"TOPIC: {topic_name}\n"
        f"KEY TERMS IN THIS SECTION: {terms_str}\n\n"
        f"TRANSCRIPT:\n{transcript[:6000]}\n\n"
        "Respond in this exact format:\n\n"
        "TEACHING SUMMARY: [2-3 sentences: what's the core concept, what's the key "
        "visual or mental model a student would remember, and what's the one exam-testable "
        "takeaway. Don't explain the content — just describe how a great tutor would frame it.]\n\n"
        "SCIENTIFIC TERMS: [comma-separated list of ALL scientific/medical terms that appear "
        "in this section. Include terms from the key terms list plus any others you identify "
        "in the transcript. Only real scientific vocabulary — not sentence fragments or filler.]\n\n"
        "SUB-CONCEPTS: [numbered list of the distinct mechanisms, processes, or ideas a "
        "student needs to understand from this section. Each one should be a specific thing "
        "that needs its own explanation — not just a term, but a mechanism or relationship. "
        "E.g. '1. Lytic cycle — attachment, penetration, biosynthesis, maturation, release' "
        "not just '1. Lytic cycle'. Be thorough — if the professor covered 5 things, list 5 things. "
        "Include the key sub-steps or components within each.]\n\n"
        "EI%: [0-100] — Quick estimate of exam importance for a health/medical student. "
        "Core mechanisms (cell transport, immune response, drug targets) score 90-100%. "
        "Classification/naming that a table handles scores 50-70%. "
        "History, discovery stories, tangential context scores below 40%.\n\n"
        "PROFESSOR SIGNALS: [List any phrases where the professor explicitly tells "
        "students to skip, ignore, or not memorize something (e.g. 'don't worry about "
        "that', 'you don't need to know', 'we'll cover that later'). Also list phrases "
        "where the professor says something IS important (e.g. 'you'll need to remember', "
        "'this will be on the exam', 'make sure you know'). Quote the exact phrase. "
        "If no explicit signals, write 'None detected.']"
    )

    try:
        response = client.models.generate_content(
            model=CHUNKER_FALLBACK_MODEL,
            contents=prompt,
            config={"temperature": 0.1, "max_output_tokens": 2048},
        )
        text = response.text.strip()

        # Parse the response
        summary = ""
        all_terms = []
        ei_est = 50
        sub_concepts = []

        summary_match = re.search(r"TEACHING SUMMARY:\s*(.+?)(?=SCIENTIFIC TERMS:|$)", text, re.DOTALL)
        terms_match = re.search(r"SCIENTIFIC TERMS:\s*(.+?)(?=SUB-CONCEPTS:|$)", text, re.DOTALL)
        subconcepts_match = re.search(r"SUB-CONCEPTS:\s*(.+?)(?=EI%:|$)", text, re.DOTALL)
        ei_match = re.search(r"EI%:\s*(\d+)", text)
        signals_match = re.search(r"PROFESSOR SIGNALS:\s*(.+?)$", text, re.DOTALL)

        if summary_match:
            summary = summary_match.group(1).strip()
        if terms_match:
            raw_terms = terms_match.group(1).strip()
            all_terms = [t.strip().strip("*").strip() for t in raw_terms.split(",") if t.strip()]
            all_terms = [t for t in all_terms if len(t) >= 3 and len(t.split()) <= 4]
        if subconcepts_match:
            raw_sc = subconcepts_match.group(1).strip()
            for line in raw_sc.split("\n"):
                line = re.sub(r"^\d+[\.\)]\s*", "", line.strip()).strip()
                if line and len(line) > 5:
                    sub_concepts.append(line)
        if ei_match:
            ei_est = max(0, min(100, int(ei_match.group(1))))
        prof_signals_text = ""
        if signals_match:
            raw_signals = signals_match.group(1).strip()
            if raw_signals.lower() != "none detected." and raw_signals.lower() != "none detected":
                prof_signals_text = raw_signals

        transcript_wc = len(transcript.split())

        return ChunkPreview(
            group_index=group_index,
            group_name=topic_name,
            teaching_summary=summary,
            new_terms=all_terms,
            prior_terms=[],
            ei_estimate=ei_est,
            transcript_words=transcript_wc,
            sub_concepts=sub_concepts,
            prof_signals=prof_signals_text,
        )
    except Exception as e:
        print(f"    [preview] Failed for '{topic_name}': {e}")
        return ChunkPreview(
            group_index=group_index,
            group_name=topic_name,
            teaching_summary=f"Covers {topic_name}.",
            new_terms=real_terms[:5],
            prior_terms=[],
            ei_estimate=50,
            transcript_words=len(transcript.split()),
            sub_concepts=[],
        )


def _assign_term_ownership(previews: list[ChunkPreview]) -> None:
    """Assign new vs prior terms across all previews using set arithmetic.

    First chunk to mention a term owns it as "new". All subsequent chunks
    that use the same term get it as "prior". Mutates previews in place.

    This is the step that makes parallel Flash possible — the sequencing
    decision is pure Python, not an LLM task.
    """
    seen: set[str] = set()

    for preview in previews:
        all_terms = preview.new_terms  # Currently holds ALL terms from Flash
        all_terms_lower = {t.lower(): t for t in all_terms}

        # Terms we haven't seen yet → new (bold on first use)
        new = [all_terms_lower[k] for k in all_terms_lower if k not in seen]
        # Terms already introduced → prior (use casually, don't re-bold)
        prior = [all_terms_lower[k] for k in all_terms_lower if k in seen]

        preview.new_terms = new
        preview.prior_terms = prior

        # Add new terms to the seen set
        seen.update(t.lower() for t in new)


def _coordinate_concept_ownership(client, previews: list[ChunkPreview]) -> None:
    """Flash coordinator: assign concept ownership across all sections.

    One Flash call that sees ALL sub-concepts from ALL chunks and detects
    semantic overlaps that string-matching misses. Assigns each concept to
    exactly one section; other sections get callback-only instructions.

    This replaces the Python string-matching in _format_previews_for_pro().
    Mutates previews in place (sets .owns and .callback_only).
    """
    # Build the coordinator prompt — compact input to save tokens
    sections_text = ""
    for p in previews:
        sc_str = ", ".join(p.sub_concepts) if p.sub_concepts else "(none)"
        sections_text += f"S{p.group_index} [{p.group_name}] EI={p.ei_estimate}%: {sc_str}\n"

    prompt = (
        "You're the coordinator in a lecture-generation pipeline. After you finish, multiple "
        "writers will generate sections of a lecture document in parallel — they can't see each "
        "other's output. The student reads all sections in order as one continuous document. "
        "If two writers both fully explain the same concept, the student reads it twice. Your job "
        "is to prevent that by assigning concept ownership.\n\n"
        "Below are the sub-concepts each section plans to cover. Detect overlapping concepts "
        "across sections — even when described with different words (e.g. 'lytic cycle — 5 steps' "
        "and 'viral multiplication — attachment to lysis' are the same concept). Assign each "
        "concept to exactly ONE section (the one with the highest EI% or most detailed coverage). "
        "Other sections get a callback instruction instead.\n\n"
        f"SECTIONS:\n{sections_text}\n\n"
        "Output ONLY the assignments. No internal reasoning. No 'Wait' or analysis. "
        "ALL " + str(len(previews)) + " sections MUST appear. One line per section.\n"
        "Keep concept names SHORT (2-4 words).\n\n"
        "Format — one line per section, exactly like this:\n"
        "S2: OWNS: acellular agents, obligate parasitism | CB: host specificity→S13\n"
        "S3: OWNS: envelope acquisition | CB: none\n"
        "S4: OWNS: none | CB: genome-size→S11, giant viruses→S11\n\n"
        "Start output now:"
    )

    try:
        response = client.models.generate_content(
            model=CHUNKER_FALLBACK_MODEL,
            contents=prompt,
            config={
                "temperature": 0.1,
                # High limit because Flash thinking tokens count against output budget.
                # Coordinator output is ~1500 chars but Flash may use ~7000 thinking tokens.
                "max_output_tokens": 32768,
            },
        )
        text = response.text.strip()
        print(f"    [coordinator] Concept ownership assigned")

        # Parse coordinator output — handles both compact and verbose formats
        for line in text.split("\n"):
            # Strip markdown formatting
            clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
            clean = re.sub(r"^\s*\*?\s*", "", clean).strip()
            if not clean:
                continue

            # Try compact format: "S7: OWNS: ... | CB: ..."
            compact = re.match(r"S(\d+)\s*:\s*(.+)", clean, re.IGNORECASE)
            # Try verbose format: "SECTION 7: ..." or "Section 7 — ..."
            verbose = re.match(r"Section\s+(\d+)\s*[—:\-]", clean, re.IGNORECASE)

            idx = None
            rest = ""
            if compact:
                idx = int(compact.group(1))
                rest = compact.group(2)
            elif verbose:
                idx = int(verbose.group(1))
                rest = clean[verbose.end():].strip()

            if idx is None:
                # Check if this is a continuation OWNS/CB line for a multi-line format
                continue

            # Find preview
            preview = None
            for p in previews:
                if p.group_index == idx:
                    preview = p
                    break
            if not preview:
                continue

            # Parse OWNS and CB from the rest of the line
            # Split on | to separate OWNS from CB
            owns_raw = ""
            cb_raw = ""

            if "|" in rest:
                parts_split = rest.split("|", 1)
                owns_raw = parts_split[0].strip()
                cb_raw = parts_split[1].strip() if len(parts_split) > 1 else ""
            else:
                owns_raw = rest

            # Extract OWNS
            owns_match = re.search(r"OWNS:\s*(.+?)(?:\||$)", owns_raw, re.IGNORECASE)
            if owns_match:
                raw = owns_match.group(1).strip().rstrip(".")
                if raw.lower() not in ("bridge only", "none"):
                    preview.owns = [c.strip() for c in raw.split(",") if c.strip() and len(c.strip()) > 2]

            # Extract CB/CALLBACK
            cb_match = re.search(r"(?:CB|CALLBACK(?:\s+ONLY)?)\s*:\s*(.+)", cb_raw or rest, re.IGNORECASE)
            if cb_match:
                raw = cb_match.group(1).strip().rstrip(".")
                if raw.lower() != "none":
                    callbacks = []
                    for part in re.split(r",\s*", raw):
                        part = part.strip()
                        if part and len(part) > 3:
                            part = part.replace("->", "→").replace("→", "→")
                            callbacks.append(part)
                    preview.callback_only = callbacks

        # Log summary
        total_owns = sum(len(p.owns) for p in previews)
        total_cb = sum(len(p.callback_only) for p in previews)
        print(f"    → Coordinator: {total_owns} owned concepts, {total_cb} callbacks")

    except Exception as e:
        print(f"    [coordinator] Failed ({e}), falling back to no coordination")
        # On failure, every section owns all its sub-concepts (current behavior)
        for p in previews:
            p.owns = list(p.sub_concepts)


def prefetch_all_previews(
    client,
    chunks: list[dict],
) -> list[ChunkPreview]:
    """Generate teaching previews for ALL chunks via Flash in parallel.

    Three phases:
    1. Parallel Flash calls (~10s): each chunk gets a teaching summary + all terms
    2. Sequential Python (~0s): assign term ownership (new vs prior) via set math
    3. Flash coordinator (~5-10s): assign concept ownership across sections

    Returns ordered list of ChunkPreview objects with terms correctly split.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Filter to teaching chunks only
    teaching = []
    for i, chunk in enumerate(chunks):
        topic_name = chunk.get("topic_name", "")
        transcript = chunk.get("transcript_text", "")
        if not _is_housekeeping(topic_name, transcript):
            teaching.append((i, chunk))

    # Phase 1: Parallel Flash calls
    previews_by_index: dict[int, ChunkPreview] = {}

    def _preview_one(idx_chunk):
        idx, chunk = idx_chunk
        return idx, _generate_single_preview(client, chunk, group_index=idx)

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(_preview_one, ic): ic[0] for ic in teaching}
        for future in as_completed(futures):
            idx, preview = future.result()
            previews_by_index[idx] = preview
            n_terms = len(preview.new_terms)
            n_sc = len(preview.sub_concepts)
            print(f"    [{idx}] {preview.group_name}: {n_terms} terms, {n_sc} sub-concepts, EI~{preview.ei_estimate}%")

    # Reassemble in order
    previews = [previews_by_index[idx] for idx, _ in teaching if idx in previews_by_index]

    # Phase 2: Assign term ownership (pure Python, instant)
    _assign_term_ownership(previews)

    total_new = sum(len(p.new_terms) for p in previews)
    total_prior = sum(len(p.prior_terms) for p in previews)
    print(f"    → Term assignment: {total_new} new, {total_prior} prior references")

    # Phase 3: Flash coordinator — assign concept ownership across sections
    _coordinate_concept_ownership(client, previews)

    return previews


def _format_previews_for_pro(
    previews: list[ChunkPreview],
    current_group_index: int,
    current_sub_concepts: list[str] | None = None,
) -> str:
    """Format coordinator assignments + prior context for Pro.

    Uses the Flash coordinator's concept ownership assignments (owns/callback_only)
    instead of Python string-matching. Pro gets precise instructions about what
    to teach and what to skip.
    """
    # Find this chunk's preview
    current_preview = None
    for p in previews:
        if p.group_index == current_group_index:
            current_preview = p
            break

    parts = []

    # Coordinator assignments — the primary dedup mechanism
    if current_preview and current_preview.callback_only:
        # Strip concept details — only show "concept name → Section N"
        # Giving Pro details (like "lytic cycle — 5 steps") tempts it to list those steps
        cb_list = "\n".join(f"  - {cb}" for cb in current_preview.callback_only)
        parts.append(
            "CALLBACK ONLY — another writer owns these. Mention by name only. "
            "Do NOT list steps, components, or mechanisms. Just 'as we covered in Section N' "
            "and move on:\n" + cb_list
        )

    if current_preview and current_preview.owns:
        owns_list = "\n".join(f"  - {o}" for o in current_preview.owns)
        parts.append(
            "YOUR SECTION OWNS THESE CONCEPTS — teach them fully:\n" + owns_list
        )

    # Prior sections summary for natural backwards connections
    prior = [p for p in previews if p.group_index < current_group_index]
    if prior:
        summary_lines = []
        for p in prior[-4:]:
            summary_lines.append(f"  Section {p.group_index}: {p.group_name} — {p.teaching_summary[:80]}")
        parts.append(
            "PREVIOUSLY COVERED (connect backwards naturally where relevant):\n"
            + "\n".join(summary_lines)
        )

    # Fallback: if coordinator didn't run, use sub-concepts as owns
    if current_preview and not current_preview.owns and not current_preview.callback_only:
        current_sc = current_sub_concepts or current_preview.sub_concepts
        if current_sc:
            sc_list = "\n".join(f"  - {sc}" for sc in current_sc)
            parts.append(
                f"SUB-CONCEPTS TO COVER:\n{sc_list}"
            )

    return "\n\n".join(parts)


def _get_new_terms_for_chunk(
    previews: list[ChunkPreview],
    current_group_index: int,
) -> tuple[list[str], list[str]]:
    """Get new vs prior terms for a specific chunk.

    Returns (new_terms_to_bold, prior_terms_already_introduced).
    """
    for p in previews:
        if p.group_index == current_group_index:
            return p.new_terms, p.prior_terms
    return [], []


# ═══════════════════════════════════════════════════════════════════════════
# Per-chunk user prompt builder
# ═══════════════════════════════════════════════════════════════════════════

def build_user_prompt(
    chunk_transcript: str,
    topic_name: str,
    key_terms: list[str],
    textbook_section: str,
    prior_groups: list[str] | None = None,
    slide_number: int = 1,
    lecture_slide_parts: list | None = None,
    slide_metadata: list[dict] | None = None,
    previews_context: str = "",
    new_terms: list[str] | None = None,
    prior_terms: list[str] | None = None,
    ei_estimate: int = 50,
    transcript_words: int = 0,
    sub_concepts: list[str] | None = None,
    textbook_images: list[dict] | None = None,
    prof_signals: str = "",
) -> list:
    """Build the per-chunk user prompt as a list of Parts.

    Ordering is deliberate: prior context → textbook (factual ground truth)
    → professor transcript (scope) → lecture slides (visual) → final instruction.
    Textbook and transcript come AFTER the creative brief (in system instruction)
    so the model absorbs style first, then applies it to content it just read.

    Returns a list of google.genai Part objects.
    """
    from google.genai import types

    parts = []

    # 1. What's been covered so far — Flash-generated previews with term tracking
    if previews_context:
        parts.append(types.Part.from_text(text=
            f"PREVIOUSLY COVERED SECTIONS (teaching summaries from earlier groups):\n\n"
            f"{previews_context}\n\n"
            "Connect backwards naturally where relevant — the way you'd say "
            "'remember the capsid we covered earlier' if you'd already taught it."
        ))

        # Term tracking for bold/unbold decisions
        if new_terms:
            parts.append(types.Part.from_text(text=
                f"TERMS TO BOLD (first introduction in THIS section): {', '.join(new_terms)}\n"
                "Bold these on first use — the student hasn't seen them before."
            ))
        if prior_terms:
            parts.append(types.Part.from_text(text=
                f"TERMS ALREADY INTRODUCED (use casually, don't re-bold): {', '.join(prior_terms)}\n"
                "These were already defined in earlier sections. Use them naturally "
                "without re-introducing or re-bolding."
            ))
    elif prior_groups:
        # Fallback: old-style prior_groups list (for single-chunk testing)
        groups_str = "\n".join(f"  {g}" for g in prior_groups)
        parts.append(types.Part.from_text(text=
            f"PREVIOUSLY COVERED GROUPS:\n{groups_str}\n\n"
            "Connect backwards naturally where relevant — the way you'd say "
            "'remember the sarcolemma' if you'd already taught it."
        ))

    # 2. OpenStax textbook reference (factual source of truth)
    if textbook_section:
        parts.append(types.Part.from_text(text=
            f"OPENSTAX TEXTBOOK REFERENCE (your factual source of truth — "
            f"if the professor contradicts this, go with the textbook):\n\n"
            f"{textbook_section}"
        ))

    # 3. Professor's raw transcript (scope, not style)
    parts.append(types.Part.from_text(text=
        f"PROFESSOR'S TRANSCRIPT FOR THIS SECTION (topic: '{topic_name}').\n"
        f"Use this for WHAT to teach, not HOW. The transcript is auto-captioned "
        f"and full of garbled terms — always use correct scientific spelling.\n\n"
        f"{chunk_transcript}"
    ))

    # 4. Key terms to make sure they're covered
    if key_terms:
        # Filter noise terms and strip trailing filler from auto-caption artifacts
        # e.g. "Ebola virus if" → "Ebola virus", "hepatitis viruses and" → "hepatitis viruses"
        _TRAILING_FILLER = re.compile(
            r"\s+(?:if|and|but|or|the|a|an|is|are|was|were|which|that|this|"
            r"so|um|uh|okay|very|also|has|have|it|its|with|for|from|"
            r"can|will|do|does|did|not|no|be|been|being|more|most|"
            r"here|there|some|into|of|in|on|at|to|as|we|our|they)$",
            re.IGNORECASE,
        )
        _LEADING_FILLER = re.compile(
            r"^(?:although|but|so|um|uh|okay|most|some|the|a|an|"
            r"we|our|they|there|now|and|or|did|has|you|its|this|"
            r"here|get)\s+",
            re.IGNORECASE,
        )
        real_terms = []
        seen = set()
        for t in key_terms:
            if len(t.split()) > 4 or len(t) < 3:
                continue
            # Strip leading and trailing filler
            cleaned = _LEADING_FILLER.sub("", t).strip()
            cleaned = _TRAILING_FILLER.sub("", cleaned).strip()
            # Apply trailing filler repeatedly (handles "which which")
            prev = None
            while cleaned != prev:
                prev = cleaned
                cleaned = _TRAILING_FILLER.sub("", cleaned).strip()
            if cleaned and len(cleaned) >= 3 and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                real_terms.append(cleaned)
        if real_terms:
            parts.append(types.Part.from_text(text=
                f"KEY TERMS FROM TRANSCRIPT: {', '.join(real_terms[:15])}\n"
                "Make sure these appear in your output with correct spelling. "
                "If any are garbled auto-caption artifacts, figure out the real term."
            ))

    # 5. Lecture slides (if available)
    if lecture_slide_parts and slide_metadata:
        # Tell Pro exactly which files these are so it can reference them in output
        slide_listing = "\n".join(
            f"  - {s['image_filename']} [{s.get('timestamp_display', '')}]: {s.get('description', '')[:120]}"
            for s in slide_metadata
        )
        parts.append(types.Part.from_text(text=
            "PROFESSOR'S LECTURE SLIDES FOR THIS SECTION. These are the actual "
            "slides the student sees in class. Use them as the primary visual in your "
            "slide doc — reference the filename so we can embed it.\n\n"
            f"{slide_listing}\n\n"
            "In your === SLIDE === output, reference the professor's slide image like:\n"
            "![description](screenshots/screenshot_00X.jpg)\n"
            "Your transcript should physically point at these slides at least once per "
            "section ('Looking at the slide, notice...', 'On the diagram you can see...')."
        ))
        parts.extend(lecture_slide_parts)
    elif lecture_slide_parts:
        parts.append(types.Part.from_text(text=
            "PROFESSOR'S LECTURE SLIDES FOR THIS SECTION:"
        ))
        parts.extend(lecture_slide_parts)

    # 5b. OpenStax textbook figures (available for diagram cards)
    if textbook_images:
        img_listing = "\n".join(
            f"  - {img['figure_id'] or 'Figure'}: {img['caption'][:120]}\n"
            f"    URL: {img['gcs_url']}"
            for img in textbook_images
            if img.get("gcs_url")
        )
        if img_listing:
            parts.append(types.Part.from_text(text=
                "OPENSTAX TEXTBOOK FIGURES AVAILABLE FOR THIS SECTION.\n"
                "These are real images we've already downloaded — use them for diagram-type "
                "slide cards instead of suggesting images. Reference them by their exact URL.\n\n"
                f"{img_listing}\n\n"
                "For diagram cards, embed the image like:\n"
                "![Figure caption](https://storage.googleapis.com/...the-exact-url...)\n\n"
                "Pick the figure that best illustrates the concept. If no figure fits, "
                "you can still write a diagram card without an image.\n\n"
                "Source: OpenStax. Download free at openstax.org. CC BY 4.0"
            ))

    # 6. Depth guidance — checklist for high-EI, bridge framing for low-EI
    depth_parts = []

    if ei_estimate >= 70:
        # High-EI: sub-concept checklist drives depth
        if sub_concepts:
            sc_list = "\n".join(f"  {i+1}. {sc}" for i, sc in enumerate(sub_concepts))
            depth_parts.append(
                f"This section scored EI {ei_estimate}% — core or important curriculum.\n\n"
                f"SUB-CONCEPTS TO COVER (each needs its own paragraph with the "
                f"mechanism explained step by step):\n{sc_list}\n\n"
                "Don't just mention these — teach each one. A student reading your "
                "explanation of each sub-concept should understand how it works, "
                "not just know it exists."
            )
    elif ei_estimate < 60:
        # Low-EI: bridge framing — reframe the task from "teach" to "transition"
        depth_parts.append(
            f"This section scored EI {ei_estimate}% — supporting knowledge.\n\n"
            "You are writing a BRIDGE PARAGRAPH, not a teaching section. "
            "The slide has the content (table, dot points, diagram). "
            "Your transcript is 2-4 sentences: point at the slide, give the 'so what', "
            "and transition to the next topic. Like the anatomy professor between "
            "major topics — quick, confident, no hand-holding."
        )

    # Professor's own exam/skip signals (from transcript)
    if prof_signals:
        depth_parts.append(
            f"PROFESSOR'S OWN SIGNALS FROM THE LECTURE:\n{prof_signals}\n"
            "Respect these — if the professor said 'don't worry about X', "
            "give X a one-liner at most. If the professor said 'you need to "
            "know X', make sure X gets thorough coverage."
        )

    if depth_parts:
        parts.append(types.Part.from_text(text=
            "DEPTH GUIDANCE:\n" + "\n\n".join(depth_parts)
        ))

    # 7. Output instruction
    parts.append(types.Part.from_text(text=
        f"\nWrite this as Slide {slide_number}. "
        "Output in this exact format:\n\n"
        "=== SLIDE ===\n"
        f"Slide {slide_number}: [Your title]\n"
        "type: professor_slide OR diagram\n"
        "[If type is professor_slide: just the image reference and one exam tip — "
        "the slide already has labels and bullet points baked in, don't duplicate them.]\n"
        "[If type is diagram: dot points providing context, then embed the best matching "
        "OpenStax figure from the AVAILABLE FIGURES list above using markdown: "
        "![caption](https://storage.googleapis.com/...). If no figures were provided, "
        "write a text suggestion instead.]\n"
        "[If this chunk needs multiple visuals, split them as Slide {slide_number}a, "
        f"Slide {slide_number}b, etc.]\n\n"
        "=== TRANSCRIPT ===\n"
        f"Slide {slide_number}\n"
        "[Your transcript — written exactly how the anatomy professor writes]\n\n"
        "=== EI% ===\n"
        "[0-100]% — [One sentence: why this score. Anything below 30%, "
        "draw a line through it in the slide and transcript.]"
    ))

    return parts


# ═══════════════════════════════════════════════════════════════════════════
# Output parser — split delimited output into structured sections
# ═══════════════════════════════════════════════════════════════════════════

def _parse_slide_cards(slide_content: str, slide_number: int, ei_percent: int) -> list[SlideCard]:
    """Parse raw slide content into structured SlideCard objects.

    Handles single slides and multi-slide chunks (1a, 1b, 1c).
    Detects card type from content: professor_slide if it references
    screenshots/, diagram if it suggests OpenStax/Wikimedia or has bullet points.
    """
    cards = []

    # Check if there are sub-slides (1a, 1b, etc.)
    sub_pattern = rf"Slide\s+{slide_number}([a-z])\s*[:.]?\s*(.*?)(?=Slide\s+{slide_number}[a-z]|$)"
    sub_matches = list(re.finditer(sub_pattern, slide_content, re.DOTALL | re.IGNORECASE))

    if sub_matches:
        blocks = [(m.group(1), m.group(2).strip()) for m in sub_matches]
    else:
        # Single slide — strip the "Slide N: Title" header
        content = re.sub(rf"^Slide\s+{slide_number}\s*[:.]?\s*", "", slide_content, flags=re.IGNORECASE).strip()
        blocks = [("", content)]

    for suffix, block in blocks:
        slide_id = f"{slide_number}{suffix}"

        # Extract title (first line or bold text)
        title = ""
        lines = block.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith(("*", "-", "!", "~", "[")):
                title = re.sub(r"\*\*(.+?)\*\*", r"\1", stripped)  # strip bold
                title = re.sub(r"^#+\s*", "", title)  # strip heading markers
                break

        # Detect image references — professor screenshots OR GCS-hosted OpenStax images
        img_refs = re.findall(r"!\[.*?\]\((screenshots/[^\)]+)\)", block)
        gcs_img_refs = re.findall(r"!\[.*?\]\((https://storage\.googleapis\.com/[^\)]+)\)", block)
        diagram_suggestions = re.findall(r"\[(?:Suggest(?:ed)?\s+)?[Dd]iagram.*?\].*", block)

        # Detect card type
        has_professor_slide = bool(img_refs)
        has_type_line = re.search(r"type:\s*(professor_slide|diagram)", block, re.IGNORECASE)

        has_gcs_image = bool(gcs_img_refs)
        if has_type_line:
            card_type = has_type_line.group(1).lower().replace(" ", "_")
        elif has_professor_slide:
            card_type = "professor_slide"
        elif has_gcs_image:
            card_type = "diagram"  # diagram with real OpenStax image
        else:
            card_type = "diagram"

        # Extract bullet points (only meaningful for diagram cards)
        bullets = []
        for line in lines:
            bullet_match = re.match(r"^\s*[\*\-\d\.]\s+(.+)", line)
            if bullet_match:
                text = bullet_match.group(1).strip()
                # Skip lines that are image refs or metadata
                if not text.startswith(("!", "[", "type:", "~~")):
                    bullets.append(text)

        # Extract exam tip — look for italic lines, or last non-image line
        exam_tip = ""
        for line in reversed(lines):
            stripped = line.strip()
            if stripped.startswith("*") and stripped.endswith("*") and "!" not in stripped:
                exam_tip = stripped.strip("* ")
                break
            # Also catch "Exam tip:" or similar
            if re.match(r"(?:exam|tip|takeaway)", stripped, re.IGNORECASE):
                exam_tip = stripped
                break

        # Extract struck-through content as low-EI items
        struck = re.findall(r"~~(.+?)~~", block, re.DOTALL)
        if struck:
            for s in struck:
                exam_tip = exam_tip or f"Low priority: {s.strip()[:80]}"

        image_ref = img_refs[0] if img_refs else ""
        if not image_ref and gcs_img_refs:
            image_ref = gcs_img_refs[0]
        if not image_ref and diagram_suggestions:
            image_ref = diagram_suggestions[0]

        cards.append(SlideCard(
            slide_id=slide_id,
            title=title,
            card_type=card_type,
            image_ref=image_ref,
            bullet_points=bullets if card_type == "diagram" else [],
            exam_tip=exam_tip,
            ei_percent=ei_percent,
        ))

    # Fallback: if no cards were parsed, create one from the raw content
    if not cards:
        cards.append(SlideCard(
            slide_id=str(slide_number),
            title=f"Slide {slide_number}",
            card_type="diagram",
            bullet_points=[],
            ei_percent=ei_percent,
        ))

    return cards


def parse_output(raw_output: str, slide_number: int = 1, group_name: str = "") -> GeneratedSection:
    """Parse the delimited model output into a GeneratedSection.

    Expected format:
        === SLIDE ===
        Slide N: Title
        type: professor_slide | diagram
        [slide content]

        === TRANSCRIPT ===
        Slide N
        [transcript text]

        === EI% ===
        XX% — reasoning
    """
    slide_content = ""
    transcript = ""
    ei_percent = 50
    ei_reasoning = ""

    # Split on delimiters — handle variations in spacing, case, and formatting
    # Pro sometimes uses "== SLIDE ==" or "=== Slide ===" or extra whitespace
    slide_match = re.search(
        r"={2,}\s*SLIDE\s*={2,}\s*\n(.*?)(?=={2,}\s*TRANSCRIPT\s*={2,})",
        raw_output, re.DOTALL | re.IGNORECASE
    )
    transcript_match = re.search(
        r"={2,}\s*TRANSCRIPT\s*={2,}\s*\n(.*?)(?=={2,}\s*EI%?\s*={2,})",
        raw_output, re.DOTALL | re.IGNORECASE
    )
    ei_match = re.search(
        r"={2,}\s*EI%?\s*={2,}\s*\n(.*)",
        raw_output, re.DOTALL | re.IGNORECASE
    )

    # Fallback: try markdown-style headers if delimiter format wasn't used
    if not slide_match:
        slide_match = re.search(
            r"#+\s*SLIDE.*?\n(.*?)(?=#+\s*TRANSCRIPT|$)", raw_output, re.DOTALL | re.IGNORECASE
        )
    if not transcript_match:
        transcript_match = re.search(
            r"#+\s*TRANSCRIPT.*?\n(.*?)(?=#+\s*EI|$)", raw_output, re.DOTALL | re.IGNORECASE
        )
    if not ei_match:
        ei_match = re.search(
            r"#+\s*EI%?.*?\n(.*)", raw_output, re.DOTALL | re.IGNORECASE
        )

    if slide_match:
        slide_content = slide_match.group(1).strip()
    if transcript_match:
        transcript = transcript_match.group(1).strip()
    if ei_match:
        ei_text = ei_match.group(1).strip()
        pct_match = re.search(r"(\d+)\s*%", ei_text)
        if pct_match:
            ei_percent = int(pct_match.group(1))
        reason_match = re.search(r"\d+\s*%\s*[\u2014\-\u2014]\s*(.*)", ei_text, re.DOTALL)
        if reason_match:
            ei_reasoning = reason_match.group(1).strip()

    # Fallback: if delimiters weren't used, treat entire output as transcript
    if not slide_content and not transcript:
        transcript = raw_output.strip()
        slide_content = f"Slide {slide_number}: [Content]"
        print(f"  [parse] WARNING: No delimiters found for Slide {slide_number} ({group_name}), using raw output as transcript")
    elif not transcript and slide_content:
        # Slide parsed but transcript didn't — likely a delimiter mismatch
        # Try to extract transcript as everything after the slide section
        remaining = raw_output[raw_output.find(slide_content) + len(slide_content):]
        # Look for "Slide N" as transcript start
        tx_start = re.search(rf"Slide\s+{slide_number}\b", remaining)
        if tx_start:
            transcript = remaining[tx_start.start():].strip()
            # Remove trailing EI section if present
            ei_cut = re.search(r"\n\d+\s*%\s*[—\-]", transcript)
            if ei_cut:
                transcript = transcript[:ei_cut.start()].strip()
            print(f"  [parse] WARNING: Transcript delimiter missing for Slide {slide_number} ({group_name}), recovered {len(transcript.split())}w from fallback")
        else:
            print(f"  [parse] ERROR: Empty transcript for Slide {slide_number} ({group_name}) — delimiter parse failed")

    # Parse slide content into structured cards
    slide_cards = _parse_slide_cards(slide_content, slide_number, ei_percent)

    return GeneratedSection(
        slide_number=slide_number,
        slide_content=slide_content,
        slide_cards=slide_cards,
        transcript=transcript,
        ei_percent=ei_percent,
        ei_reasoning=ei_reasoning,
        group_name=group_name,
        raw_output=raw_output,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Section generator — single Pro call per chunk
# ═══════════════════════════════════════════════════════════════════════════

def generate_section(
    client,
    chunk_transcript: str,
    topic_name: str,
    key_terms: list[str],
    textbook_section: str,
    prior_groups: list[str] | None = None,
    slide_number: int = 1,
    lecture_slide_parts: list | None = None,
    slide_metadata: list[dict] | None = None,
    cache_name: str | None = None,
    model: str | None = None,
    previews_context: str = "",
    new_terms: list[str] | None = None,
    prior_terms: list[str] | None = None,
    ei_estimate: int = 50,
    transcript_words: int = 0,
    sub_concepts: list[str] | None = None,
    textbook_images: list[dict] | None = None,
    prof_signals: str = "",
) -> GeneratedSection:
    """Generate one section: slide + transcript + EI%.

    Uses the cached creative brief (if available) or includes system
    instruction directly. One API call per chunk.
    """
    from google.genai import types

    model = model or GENERATOR_MODEL

    # Build user prompt — anatomy slide images go first (can't be in system_instruction)
    all_user_parts = []

    # Anatomy reference images (first call only? no — include every time,
    # they're cheap at ~258 tokens each and essential for style transfer)
    ref_image_parts = build_creative_brief_image_parts()
    all_user_parts.extend(ref_image_parts)

    # Then the per-chunk content
    chunk_parts = build_user_prompt(
        chunk_transcript=chunk_transcript,
        topic_name=topic_name,
        key_terms=key_terms,
        textbook_section=textbook_section,
        prior_groups=prior_groups,
        slide_number=slide_number,
        lecture_slide_parts=lecture_slide_parts,
        slide_metadata=slide_metadata,
        previews_context=previews_context,
        new_terms=new_terms,
        prior_terms=prior_terms,
        ei_estimate=ei_estimate,
        transcript_words=transcript_words,
        sub_concepts=sub_concepts,
        textbook_images=textbook_images,
        prof_signals=prof_signals,
    )
    all_user_parts.extend(chunk_parts)

    # Build generation config
    gen_config = {
        "temperature": 0.7,
        "max_output_tokens": 8192,
    }

    if cache_name:
        # Use cached content — tools and system_instruction are IN the cache,
        # cannot be set again in the request
        gen_config["cached_content"] = cache_name
    else:
        # No cache — include system instruction and tools directly
        gen_config["system_instruction"] = build_system_instruction_text()
        gen_config["tools"] = [{"google_search": {}}]

    try:
        response = client.models.generate_content(
            model=model,
            contents=all_user_parts,
            config=gen_config,
        )
        raw = response.text
    except Exception as e:
        print(f"  [error] Generation failed for '{topic_name}': {e}")
        raw = f"[Generation failed: {e}]"

    return parse_output(raw, slide_number=slide_number, group_name=topic_name)


# ═══════════════════════════════════════════════════════════════════════════
# Lecture generator — full orchestrator
# ═══════════════════════════════════════════════════════════════════════════

def _load_screenshots_json(screenshots_path: str | Path) -> list[dict]:
    """Load screenshots.json metadata."""
    import json
    screenshots_path = Path(screenshots_path)
    if not screenshots_path.exists():
        return []
    with open(screenshots_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_chunk_slides(
    chunk_index: int,
    all_screenshots: list[dict],
    screenshots_dir: Path,
) -> tuple[list, list[dict]]:
    """Get the image Parts and metadata for slides matched to a specific chunk.

    Returns (image_parts, metadata_list) for this chunk only.
    """
    from google.genai import types

    matched = [s for s in all_screenshots if s.get("matched_chunk_index") == chunk_index]
    if not matched:
        return [], []

    parts = []
    for s in matched:
        img_path = screenshots_dir / s["image_filename"]
        if img_path.exists():
            with open(img_path, "rb") as f:
                img_bytes = f.read()
            mime = "image/jpeg" if img_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
            parts.append(types.Part.from_bytes(data=img_bytes, mime_type=mime))

    return parts, matched


def generate_lecture(
    chunks: list[dict],
    lecture_slides_path: str | Path | None = None,
    screenshots_json: str | Path | None = None,
    subject: str | None = None,
    model: str | None = None,
    dry_run: bool = False,
    parallel: bool = True,
    job_id: str = "",
) -> list[GeneratedSection]:
    """Generate a complete lecture replacement from Stage 1 chunks.

    Pipeline (parallel mode):
    1. Flash prefetch: teaching summaries + term tracking for all chunks (sequential, ~30s)
    2. Flash textbook fetch: all chunks in parallel (~25s total instead of 25s × N)
    3. Context cache: create once for creative brief
    4. Pro generation: all chunks in parallel (~40s total instead of 40s × N)
    5. Clean up cache

    With parallel=True, total time ≈ 30s (prefetch) + 25s (textbook) + 45s (Pro) ≈ 100s
    With parallel=False, total time ≈ 30s + 65s × N chunks ≈ 13 min for 12 chunks

    Args:
        chunks: List of dicts with keys: transcript_text, topic_name, key_terms,
                and optionally chunk_index for screenshot mapping
        lecture_slides_path: Path to lecture slides PDF (fallback if no screenshots)
        screenshots_json: Path to screenshots.json with per-chunk slide mapping
        subject: Subject area hint for textbook search (e.g., "microbiology")
        model: Override generation model
        dry_run: If True, print prompts but don't call Pro
        parallel: If True, run textbook fetches and Pro calls in parallel
    """
    from google import genai
    from concurrent.futures import ThreadPoolExecutor, as_completed

    client = genai.Client(
        vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION
    )
    model = model or GENERATOR_MODEL

    # ── Validate content match (cheap Flash check before expensive generation) ──
    if lecture_slides_path:
        # Combine first few chunks of transcript for validation
        all_transcript = " ".join(c.get("transcript_text", "")[:500] for c in chunks[:3])
        print(f"  [validate] Checking slides match transcript...")
        validation = validate_content_match(all_transcript, slides_path=lecture_slides_path)
        if not validation.is_match and validation.confidence > 0.7:
            print(f"\n  {'='*60}")
            print(f"  ❌ CONTENT MISMATCH DETECTED")
            print(f"     Transcript topic: {validation.transcript_topic}")
            print(f"     Slides topic:     {validation.slides_topic}")
            print(f"     Confidence:       {validation.confidence:.0%}")
            print(f"     Reason:           {validation.reason}")
            print(f"  {'='*60}")
            print(f"\n  The uploaded slides don't appear to match the lecture transcript.")
            print(f"  Pipeline aborted to avoid wasting tokens on mismatched content.")
            print(f"  Please check that you uploaded the correct slides for this lecture.\n")
            return []
        elif not validation.is_match:
            print(f"  [validate] Low-confidence mismatch ({validation.confidence:.0%}): {validation.reason}")
            print(f"  [validate] Proceeding anyway — but check the output.")
        else:
            print(f"  [validate] ✓ Content match confirmed ({validation.confidence:.0%})")

    # ── Load screenshots ──
    all_screenshots = []
    screenshots_dir = None
    if screenshots_json:
        all_screenshots = _load_screenshots_json(screenshots_json)
        screenshots_dir = Path(screenshots_json).parent / "screenshots"
        print(f"  [slides] Loaded {len(all_screenshots)} screenshot(s)")

    # PDF slides are now extracted as individual images by pipeline.py
    # and passed via screenshots_json — no whole-PDF fallback needed

    # ── Filter teaching chunks ──
    teaching_chunks = []
    for i, chunk in enumerate(chunks):
        topic_name = chunk.get("topic_name", f"Section {i+1}")
        transcript = chunk.get("transcript_text", "")
        if _is_housekeeping(topic_name, transcript):
            print(f"  [skip] {topic_name} (housekeeping)")
            continue
        teaching_chunks.append((i, chunk))

    print(f"\n{'='*60}")
    print(f"  Teaching chunks: {len(teaching_chunks)} (skipped {len(chunks) - len(teaching_chunks)} housekeeping)")
    print(f"  Model: {model}")
    print(f"  Mode: {'parallel' if parallel else 'sequential'}")
    print(f"{'='*60}")

    # ══════════════════════════════════════════════════════════════
    # Stage 1+2: Flash prefetch + textbook fetch IN PARALLEL
    # These are independent — prefetch needs transcript, textbook needs topic/terms
    # Running together saves ~20-30s vs sequential
    # ══════════════════════════════════════════════════════════════
    print(f"\n  Stage 1+2: Flash prefetch + textbook fetch (parallel)...")
    t0_both = time.time()

    textbook_sections: dict[int, str] = {}
    textbook_images: dict[int, list[dict]] = {}
    previews = []

    if parallel:
        def _do_prefetch():
            return prefetch_all_previews(client, [c for _, c in teaching_chunks])

        def _fetch_one(idx_chunk):
            idx, chunk = idx_chunk
            return idx, fetch_textbook_section(
                topic_name=chunk.get("topic_name", ""),
                key_terms=chunk.get("key_terms", []),
                subject=subject,
            )

        def _fetch_images_one(idx_chunk):
            idx, chunk = idx_chunk
            return idx, fetch_textbook_images(
                topic_name=chunk.get("topic_name", ""),
                key_terms=chunk.get("key_terms", []),
                job_id=job_id,
            )

        with ThreadPoolExecutor(max_workers=8) as executor:
            # Submit prefetch as one big task
            prefetch_future = executor.submit(_do_prefetch)

            # Submit all textbook fetches individually
            textbook_futures = {executor.submit(_fetch_one, ic): ic[0] for ic in teaching_chunks}

            # Submit all image fetches in parallel too
            image_futures = {executor.submit(_fetch_images_one, ic): ic[0] for ic in teaching_chunks}

            # Collect textbook results as they complete
            for future in as_completed(textbook_futures):
                idx, text = future.result()
                textbook_sections[idx] = text
                topic = teaching_chunks[[i for i, (ci, _) in enumerate(teaching_chunks) if ci == idx][0]][1].get("topic_name", "")
                print(f"    [textbook {idx}] {topic}: {len(text)} chars")

            # Collect image results
            for future in as_completed(image_futures):
                idx, images = future.result()
                textbook_images[idx] = images

            # Collect prefetch result
            previews = prefetch_future.result()
            print(f"    [prefetch] {len(previews)} previews done")
    else:
        previews = prefetch_all_previews(client, [c for _, c in teaching_chunks])
        for idx, chunk in teaching_chunks:
            text = fetch_textbook_section(
                topic_name=chunk.get("topic_name", ""),
                key_terms=chunk.get("key_terms", []),
                subject=subject,
            )
            textbook_sections[idx] = text
            textbook_images[idx] = fetch_textbook_images(
                topic_name=chunk.get("topic_name", ""),
                key_terms=chunk.get("key_terms", []),
                job_id=job_id,
            )

    total_images = sum(len(imgs) for imgs in textbook_images.values())
    t_both = time.time() - t0_both
    print(f"  → {len(previews)} previews + {len(textbook_sections)} textbooks + {total_images} images in {t_both:.1f}s")

    if dry_run:
        for p in previews:
            print(f"\n  [{p.group_index+1}] {p.group_name}")
            print(f"    Summary: {p.teaching_summary[:100]}...")
            print(f"    New terms: {', '.join(p.new_terms[:8])}")
        print("\n  [dry-run] Done.")
        return []

    # ══════════════════════════════════════════════════════════════
    # Stage 3: Pro generation — parallel with Flash previews as context
    # ══════════════════════════════════════════════════════════════
    cache_name = get_or_create_cache(client, model=model)
    print(f"\n  Stage 3: Pro generation ({'parallel' if parallel else 'sequential'})...")
    t0_gen = time.time()

    # Pre-compute per-chunk context
    chunk_contexts = []
    for slide_number, (orig_idx, chunk) in enumerate(teaching_chunks, start=1):
        topic_name = chunk.get("topic_name", "")
        chunk_index = chunk.get("chunk_index", orig_idx)

        # Look up Flash's EI estimate and sub-concepts for this chunk
        ei_est = 50
        transcript_wc = 0
        sub_concepts = []
        prof_signals = ""
        for p in previews:
            if p.group_index == orig_idx:
                ei_est = p.ei_estimate
                transcript_wc = p.transcript_words
                sub_concepts = p.sub_concepts
                prof_signals = p.prof_signals
                break

        # Prior previews context (hard constraint format)
        previews_ctx = _format_previews_for_pro(previews, orig_idx, sub_concepts)
        new_terms, prior_terms = _get_new_terms_for_chunk(previews, orig_idx)

        # Slides for this chunk
        chunk_slide_parts = None
        chunk_slide_meta = None
        if all_screenshots and screenshots_dir:
            chunk_slide_parts, chunk_slide_meta = _get_chunk_slides(
                chunk_index, all_screenshots, screenshots_dir
            )
        # (PDF slides come via screenshots_json, no whole-PDF fallback)

        chunk_contexts.append({
            "orig_idx": orig_idx,
            "slide_number": slide_number,
            "topic_name": topic_name,
            "transcript": chunk.get("transcript_text", ""),
            "key_terms": chunk.get("key_terms", []),
            "textbook": textbook_sections.get(orig_idx, ""),
            "textbook_images": textbook_images.get(orig_idx, []),
            "previews_ctx": previews_ctx,
            "new_terms": new_terms,
            "prior_terms": prior_terms,
            "slide_parts": chunk_slide_parts,
            "slide_meta": chunk_slide_meta,
            "ei_estimate": ei_est,
            "transcript_words": transcript_wc,
            "sub_concepts": sub_concepts,
            "prof_signals": prof_signals,
        })

    sections: list[GeneratedSection] = [None] * len(chunk_contexts)  # type: ignore

    def _generate_one(ctx):
        return ctx["slide_number"], generate_section(
            client=client,
            chunk_transcript=ctx["transcript"],
            topic_name=ctx["topic_name"],
            key_terms=ctx["key_terms"],
            textbook_section=ctx["textbook"],
            slide_number=ctx["slide_number"],
            lecture_slide_parts=ctx["slide_parts"],
            slide_metadata=ctx["slide_meta"],
            cache_name=cache_name,
            model=model,
            previews_context=ctx["previews_ctx"],
            new_terms=ctx["new_terms"],
            prior_terms=ctx["prior_terms"],
            ei_estimate=ctx["ei_estimate"],
            transcript_words=ctx["transcript_words"],
            sub_concepts=ctx["sub_concepts"],
            textbook_images=ctx.get("textbook_images", []),
            prof_signals=ctx.get("prof_signals", ""),
        )

    if parallel:
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(_generate_one, ctx): ctx["slide_number"] for ctx in chunk_contexts}
            for future in as_completed(futures):
                slide_num, section = future.result()
                idx = slide_num - 1
                sections[idx] = section
                print(f"    [Slide {slide_num}] {section.group_name}: EI={section.ei_percent}%")
    else:
        for ctx in chunk_contexts:
            slide_num, section = _generate_one(ctx)
            sections[slide_num - 1] = section
            print(f"    [Slide {slide_num}] {section.group_name}: EI={section.ei_percent}%")

    t_gen = time.time() - t0_gen

    # Filter out any None entries (shouldn't happen but safety)
    sections = [s for s in sections if s is not None]

    # Clean up cache
    clear_cache(client)

    t_total = time.time() - t0_both
    print(f"\n  {'='*50}")
    print(f"  Done. {len(sections)} sections in {t_total:.0f}s")
    print(f"    Prefetch+Textbook: {t_both:.1f}s")
    print(f"    Generate:          {t_gen:.1f}s")
    print(f"  {'='*50}\n")

    return sections, textbook_images


# ═══════════════════════════════════════════════════════════════════════════
# Housekeeping detection
# ═══════════════════════════════════════════════════════════════════════════

_HOUSEKEEPING_PATTERNS = re.compile(
    r"housekeeping|introduction\s*/\s*housekeeping|admin|assessment\s+timeline"
    r"|course\s+overview|module\s+overview|lecture\s+overview",
    re.IGNORECASE,
)


def _is_housekeeping(topic_name: str, transcript: str) -> bool:
    """Detect housekeeping/admin chunks that should be skipped."""
    if _HOUSEKEEPING_PATTERNS.search(topic_name):
        return True
    # Very short chunks with no real content
    word_count = len(transcript.split())
    if word_count < 80:
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════════
# Assembly — combine sections into final documents
# ═══════════════════════════════════════════════════════════════════════════

def assemble_slide_doc(sections: list[GeneratedSection]) -> str:
    """Assemble all slide sections into a single slide document."""
    parts = []
    for s in sections:
        if s.ei_percent < 30:
            parts.append(f"~~{s.slide_content}~~\n\n*(EI{s.ei_percent}% — {s.ei_reasoning})*")
        else:
            parts.append(s.slide_content)
    return "\n\n---\n\n".join(parts)


def assemble_transcript_doc(sections: list[GeneratedSection]) -> str:
    """Assemble all transcript sections into a single transcript document."""
    parts = []
    for s in sections:
        if s.ei_percent < 30:
            parts.append(f"~~{s.transcript}~~\n\n*(EI{s.ei_percent}% — {s.ei_reasoning})*")
        else:
            parts.append(s.transcript)
    return "\n\n---\n\n".join(parts)


def assemble_api_response(sections: list[GeneratedSection]) -> dict:
    """Assemble the structured API response for the frontend.

    Returns the format the React frontend expects:
    {
        "slides": [...],      // SlideCard data for the left panel
        "transcript": [...],  // Narrative data for the right panel
    }
    """
    slides = []
    transcript = []

    for s in sections:
        # Each section can produce multiple slide cards (1a, 1b, etc.)
        for card in s.slide_cards:
            slides.append({
                "slide_id": card.slide_id,
                "title": card.title,
                "card_type": card.card_type,
                "image_ref": card.image_ref,
                "bullet_points": card.bullet_points,
                "exam_tip": card.exam_tip,
                "ei_percent": card.ei_percent,
            })

        transcript.append({
            "slide_number": s.slide_number,
            "title": s.group_name,
            "narrative": s.transcript,
            "ei_percent": s.ei_percent,
            "ei_reasoning": s.ei_reasoning,
        })

    return {
        "slides": slides,
        "transcript": transcript,
    }
