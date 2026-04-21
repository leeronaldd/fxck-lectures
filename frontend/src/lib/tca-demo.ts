import type { SlideCard, TranscriptSection } from "./types";

export const TCA_DEMO_SLIDES: SlideCard[] = [
  {
    "slide_id": "1",
    "title": "The TCA Cycle",
    "card_type": "professor_slide",
    "image_ref": "/tca-demo/screenshot_001.png",
    "bullet_points": [
      "Completes the oxidation of carbon to CO2",
      "Occurs in the mitochondrial matrix",
      "Generates energy and metabolic intermediates"
    ],
    "exam_tip": "Remember that the TCA cycle completely oxidizes two-carbon units and provides intermediates for pathways like fatty acid synthesis.",
    "ei_percent": 85
  },
  {
    "slide_id": "4",
    "title": "Sources of Acetate",
    "card_type": "professor_slide",
    "image_ref": "/tca-demo/screenshot_004.png",
    "bullet_points": [
      "Pyruvate from glycolysis provides 2-carbon units",
      "Fat breakdown and ethanol metabolism also yield acetate",
      "TCA cycle acts as a central metabolic hub"
    ],
    "exam_tip": "Pyruvate must lose a carbon as CO2 to become the 2-carbon acetate needed for the cycle.",
    "ei_percent": 80
  },
  {
    "slide_id": "5",
    "title": "The Citrate Cycle Overview",
    "card_type": "professor_slide",
    "image_ref": "/tca-demo/screenshot_005.png",
    "bullet_points": [
      "2-carbon Acetyl-CoA + 4-carbon Oxaloacetate = 6-carbon Citrate",
      "Thioester bond activates the acetate",
      "Cycle releases 2 CO2 and regenerates oxaloacetate"
    ],
    "exam_tip": "The thioester bond on acetyl-CoA is high-energy and drives the formation of citrate.",
    "ei_percent": 95
  },
  {
    "slide_id": "10",
    "title": "Pyruvate to Acetyl-CoA",
    "card_type": "professor_slide",
    "image_ref": "/tca-demo/screenshot_010.png",
    "bullet_points": [
      "Decarboxylation removes CO2",
      "Oxidation reduces NAD+ to NADH",
      "Coenzyme A attaches to form Acetyl-CoA"
    ],
    "exam_tip": "This single reaction achieves decarboxylation, oxidation, and acylation simultaneously.",
    "ei_percent": 90
  },
  {
    "slide_id": "13",
    "title": "Mitochondrial Compartmentalization",
    "card_type": "professor_slide",
    "image_ref": "/tca-demo/screenshot_013.png",
    "bullet_points": [
      "Glycolysis in cytosol, TCA in mitochondrial matrix",
      "Pyruvate is transported across the membrane",
      "Acetyl-CoA is synthesized inside the matrix"
    ],
    "exam_tip": "Acetyl-CoA is too large to cross the mitochondrial membrane; the cell must transport pyruvate instead.",
    "ei_percent": 85
  },
  {
    "slide_id": "17",
    "title": "The Five Cofactors",
    "card_type": "professor_slide",
    "image_ref": "/tca-demo/screenshot_017.png",
    "bullet_points": [
      "TPP+ handles decarboxylation",
      "NAD+, FAD, and Lipoic acid carry electrons",
      "Coenzyme A provides the acyl carrier"
    ],
    "exam_tip": "Multiple electron carriers allow the cell to release energy in safe, stepwise increments.",
    "ei_percent": 95
  },
  {
    "slide_id": "20",
    "title": "Coenzyme A and Acylation",
    "card_type": "professor_slide",
    "image_ref": "/tca-demo/screenshot_020.png",
    "bullet_points": [
      "Facilitates acylation reactions",
      "Forms a high-energy thioester bond",
      "Activates the carbon for transfer"
    ],
    "exam_tip": "An acylation reaction transfers a carbon chain of two or more carbons onto another molecule.",
    "ei_percent": 80
  },
  {
    "slide_id": "25",
    "title": "Structure of Coenzyme A",
    "card_type": "professor_slide",
    "image_ref": "/tca-demo/screenshot_025.png",
    "bullet_points": [
      "Derived from the vitamin pantothenic acid",
      "Contains an ADP handle with an extra phosphate",
      "Active site is a single sulfur atom"
    ],
    "exam_tip": "The massive size of CoA provides a handle for enzymes to grip, preventing it from crossing membranes.",
    "ei_percent": 85
  },
  {
    "slide_id": "26",
    "title": "FAD Structure",
    "card_type": "professor_slide",
    "image_ref": "/tca-demo/screenshot_026.png",
    "bullet_points": [
      "Flavin adenine dinucleotide (FAD)",
      "Derived from vitamin B2 (riboflavin)",
      "Contains an open-chain ribitol instead of ribose"
    ],
    "exam_tip": "The active business end of FAD is the flavin ring, which accepts electrons.",
    "ei_percent": 85
  },
  {
    "slide_id": "28",
    "title": "FAD Redox Chemistry",
    "card_type": "professor_slide",
    "image_ref": "/tca-demo/screenshot_028.png",
    "bullet_points": [
      "Accepts a hydride ion to become reduced",
      "Oxidized FAD is yellow due to conjugated bonds",
      "Reduced FADH2 is colorless"
    ],
    "exam_tip": "You can visually track FAD reduction because the molecule shifts from yellow to colorless.",
    "ei_percent": 90
  },
  {
    "slide_id": "32",
    "title": "Lipoic Acid",
    "card_type": "professor_slide",
    "image_ref": "/tca-demo/screenshot_032.png",
    "bullet_points": [
      "Acts as an electron and acyl carrier",
      "Active site is a disulfide bond",
      "Reduces to two independent thiol groups"
    ],
    "exam_tip": "Lipoic acid uses a disulfide bond to trap electrons, similar to structural disulfide bonds in proteins.",
    "ei_percent": 85
  },
  {
    "slide_id": "35",
    "title": "The PDH Complex",
    "card_type": "professor_slide",
    "image_ref": "/tca-demo/screenshot_035.png",
    "bullet_points": [
      "Pyruvate dehydrogenase complex (PDH/PDC)",
      "Located on the matrix side of the inner membrane",
      "Tethers enzymes together for substrate channeling"
    ],
    "exam_tip": "The PDH complex prevents intermediates from floating away, drastically speeding up the reaction.",
    "ei_percent": 95
  },
  {
    "slide_id": "38",
    "title": "PDH Subunits",
    "card_type": "professor_slide",
    "image_ref": "/tca-demo/screenshot_038.png",
    "bullet_points": [
      "E1 binds TPP+",
      "E2 binds Lipoic acid",
      "E3 binds FAD"
    ],
    "exam_tip": "Know which cofactor is permanently attached to which enzyme subunit (E1, E2, E3).",
    "ei_percent": 90
  },
  {
    "slide_id": "40",
    "title": "E1 Mechanism Initiation",
    "card_type": "professor_slide",
    "image_ref": "/tca-demo/screenshot_040.png",
    "bullet_points": [
      "TPP+ on E1 attacks pyruvate",
      "Catalyzes alpha-decarboxylation to release CO2",
      "Prepares to hand off the 2-carbon unit to E2"
    ],
    "exam_tip": "The first step of the PDH mechanism is identical to ethanol fermentation: TPP-mediated decarboxylation.",
    "ei_percent": 90
  }
];

export const TCA_DEMO_TRANSCRIPT: TranscriptSection[] = [
  {
    "slide_number": 1,
    "title": "The TCA Cycle",
    "narrative": "Last time we looked at glycolysis, which breaks a six-carbon glucose down into two molecules of three-carbon pyruvate. But if you stop there, you're leaving a massive amount of energy on the table. There's still a lot of energy locked up in those carbon-carbon and carbon-hydrogen bonds. To get the rest of that energy out, cells need a way to completely oxidize those carbon atoms all the way down to CO2. They do this using a continuous, circular metabolic pathway called the <mark>TCA cycle</mark>.\n\nIt goes by a few names. You'll hear it called the <mark>tricarboxylic acid cycle</mark>, the citric acid cycle, or the <mark>Krebs cycle</mark>, named after <mark>Hans Krebs</mark> who mapped it out in the early part of the 20th century. The whole point of this cycle is to take two-carbon units—derived from pyruvate or other sources—and completely oxidize them. As those carbons are oxidized and released as CO2, the cycle captures the released energy in the form of high-energy electrons. \n\nBut it's not just a furnace for burning carbon. The cycle also acts as a manufacturing hub. As molecules progress through the cycle, they form various intermediates that the cell can siphon off to build completely different things, like using citrate to synthesize <mark>fatty acids</mark>. It's a dual-purpose engine running right in the middle of your cells.",
    "ei_percent": 85,
    "ei_reasoning": "Introduces the foundational purpose and alternative names of the TCA cycle."
  },
  {
    "slide_number": 4,
    "title": "Sources of Acetate",
    "narrative": "So, where do these two-carbon units actually come from? If we're starting with glucose, glycolysis gives us a three-carbon molecule called <mark>pyruvate</mark>. To get a two-carbon unit, we have to chop off one carbon as CO2. \n\nWe can also get two-carbon units from breaking down fat, or even from metabolizing <mark>ethanol</mark>. In ethanol metabolism, you end up with <mark>acetaldehyde</mark>. But for the TCA cycle, we need that two-carbon unit to be fully oxidized into an acid—specifically, acetate. The cycle is incredibly versatile because it acts as a central hub: whether you're burning carbs, fats, or alcohol, they all get funneled into two-carbon acetate groups to be burned for energy. The cell doesn't care where the carbon came from; once it's acetate, it goes into the cycle.",
    "ei_percent": 80,
    "ei_reasoning": "Connects upstream pathways (glycolysis, fat, ethanol) to the starting material of the TCA cycle."
  },
  {
    "slide_number": 5,
    "title": "The Citrate Cycle Overview",
    "narrative": "Let's look at how this cycle actually turns. The concept of a cycle means the starting material has to be regenerated at the end. The cycle officially begins when a two-carbon acetate group is handed off to a four-carbon acceptor molecule. You might remember this four-carbon molecule from gluconeogenesis: it's <mark>oxaloacetate</mark>. When you use an enzyme to stitch a two-carbon acetate and a four-carbon oxaloacetate together, you get a brand new six-carbon molecule. That six-carbon product is <mark>citrate</mark>.\n\nIf you look at the chemical structure of citrate, it has three separate carboxylic acid groups hanging off of it. This is exactly why it's called the tricarboxylic acid cycle. But the two-carbon acetate doesn't just float into the cycle on its own. Acetate by itself is relatively stable and unreactive. To force it to bind to oxaloacetate, the cell attaches it to a massive carrier molecule called Coenzyme A, forming <mark>acetyl-CoA</mark>. The bond holding the acetate to the CoA is a <mark>thioester bond</mark>. Thioester bonds are highly reactive—they activate the acetate, making that carbon desperate to leave the CoA and attack the oxaloacetate. Once the citrate is formed, the cycle proceeds through a series of steps to slowly oxidize it, ripping off two carbons as CO2, and eventually regenerating the four-carbon oxaloacetate so the cycle can run again.",
    "ei_percent": 95,
    "ei_reasoning": "Explains the core loop of the cycle and the critical role of the thioester bond in driving the first step."
  },
  {
    "slide_number": 10,
    "title": "Pyruvate to Acetyl-CoA",
    "narrative": "If most organisms are running on glucose, they have a slight geometric problem. Glycolysis gives us a three-carbon molecule (pyruvate), but the TCA cycle only accepts two-carbon molecules (acetyl-CoA). So, we need a way to turn three-carbon pyruvate into two-carbon acetyl-CoA. This isn't a simple one-step chop. It's a highly complex chemical transformation that achieves three things at once.\n\nFirst, you have to physically remove one carbon. You do this by decarboxylating the pyruvate—ripping off its carboxyl group and releasing it as a molecule of CO2. Second, look at the oxidation states. Pyruvate is an <mark>alpha keto acid</mark>. If you just chop off the CO2, you're left with an aldehyde (acetaldehyde). But acetyl-CoA is based on acetate, which is an acid. That means the carbon we're keeping has to be oxidized. As it gets oxidized, it loses two electrons. Those electrons don't just vanish; they are handed off to an electron carrier, reducing <mark>NAD$^+$</mark> into <mark>NADH</mark>. Finally, we have to attach that highly reactive <mark>S-CoA</mark> group to make the final acetyl-CoA product. Decarboxylation, oxidation, and attaching a massive coenzyme—all of this has to happen together in one coordinated mechanism.",
    "ei_percent": 90,
    "ei_reasoning": "Breaks down the three simultaneous chemical changes required to prepare pyruvate for the TCA cycle."
  },
  {
    "slide_number": 13,
    "title": "Mitochondrial Compartmentalization",
    "narrative": "Before we get into the chemical weeds of how that reaction works, we need to talk about location. Glycolysis happens out in the <mark>cytosol</mark>. But the TCA cycle happens inside the <mark>mitochondrial matrix</mark>. This compartmentalization is deliberate: it lets the eukaryotic cell maintain completely different chemical conditions for different pathways.\n\nBecause the TCA cycle is locked inside the mitochondria, the pyruvate made in the cytosol has to be transported across the mitochondrial membranes. Acetyl-CoA is way too big to cross the membrane, so the cell ships the smaller pyruvate molecule inside first, and *then* converts it to acetyl-CoA. To get pyruvate inside, the cell uses a specific transporter called the <mark>pyruvate carrier</mark>. It's easy to think we know everything about metabolism, but the actual identity of this pyruvate carrier wasn't discovered until <mark>2012</mark>. It's a great reminder that foundational metabolic pathways still have hidden secrets.",
    "ei_percent": 85,
    "ei_reasoning": "Sets the spatial context of the reaction and introduces the transport constraint."
  },
  {
    "slide_number": 17,
    "title": "The Five Cofactors",
    "narrative": "Once pyruvate is inside the matrix, it's time to convert it to acetyl-CoA. Because this reaction involves decarboxylation, oxidation, and attaching a new group, it requires a whole team of helper molecules called cofactors. You already know two of them. We need <mark>thiamine pyrophosphate</mark> (TPP$^+$) to handle the alpha-decarboxylation, just like in ethanol fermentation. And we need NAD$^+$ to catch the electrons from the oxidation.\n\nBut we also need three more: Coenzyme A (which provides the S-CoA group), and two extra electron carriers called <mark>FAD</mark> and <mark>lipoic acid</mark>. Why so many electron carriers? Having a chain of multiple carriers allows the cell to transfer electrons in careful, stepwise increments rather than one explosive release. This stepwise bucket-brigade is the entire secret to how cells safely extract energy without just bursting into flames.",
    "ei_percent": 95,
    "ei_reasoning": "Lists the required molecular machinery and explains the energetic rationale for multiple carriers."
  },
  {
    "slide_number": 20,
    "title": "Coenzyme A and Acylation",
    "narrative": "Let's look at these new cofactors, starting with Coenzyme A. You'll see this molecule constantly in biochemistry, and its main job is to facilitate <mark>acylation reactions</mark>. An acylation reaction is just a fancy way of saying 'attaching a carbon chain that's two carbons or longer onto something else.'\n\nWhen Coenzyme A attaches to acetate, it forms a thioester bond. That sulfur-carbon bond is unstable and high-energy. It effectively 'activates' the carbon next to it, making it a great leaving group. This is exactly what allows the two-carbon acetate to forcefully attach to oxaloacetate to form citrate. Without Coenzyme A priming the acetate, that bond formation wouldn't happen.",
    "ei_percent": 80,
    "ei_reasoning": "Defines the specific chemical role of CoA in driving the cycle forward."
  },
  {
    "slide_number": 25,
    "title": "Structure of Coenzyme A",
    "narrative": "When we write out the reaction and use the abbreviation 'S-CoA' or 'acetyl-CoA', it creates a misleading visual. It looks like a tiny little sulfur tag attached to a two-carbon acetate. In reality, Coenzyme A is a massive, sprawling molecule that dwarfs the two-carbon acetate it carries. It's built from <mark>pantothenic acid</mark>, which you might recognize from the side of your morning cereal box as a standard B-vitamin.\n\nThe active end of the molecule—the part that actually does the chemistry—is just a simple sulfur atom at the very tip. That's the 'S' in S-CoA. But that sulfur is attached to a long pantothenic acid chain, which is then esterified to two phosphate groups. Those phosphates are then attached to an ADP molecule that has an extra phosphate tacked onto its 3-prime carbon. It's a gigantic, bulky handle. Why does the cell use such a huge handle for such a tiny two-carbon payload? Because enzymes need something to grab onto. The sheer size of Coenzyme A gives the enzymes a massive surface area to bind, ensuring the acetate is held in exactly the right position. It's also exactly why the cell can't transport acetyl-CoA across the mitochondrial membrane—it's just too big—and has to transport the much smaller pyruvate instead.",
    "ei_percent": 85,
    "ei_reasoning": "Deconstructs the structure of CoA to explain both its enzymatic binding properties and membrane transport limitations."
  },
  {
    "slide_number": 26,
    "title": "FAD Structure",
    "narrative": "The next cofactor is FAD, which stands for <mark>flavin adenine dinucleotide</mark>. Just like NAD$^+$, FAD is an electron carrier. And just like Coenzyme A, it's built from a vitamin. FAD is derived from <mark>riboflavin</mark>, also known as <mark>vitamin B2</mark>.\n\nStructurally, FAD looks a lot like NAD$^+$. It has an ADP molecule on one end serving as a handle. But instead of a ribose sugar, it has a <mark>ribitol</mark> chain—a five-carbon chain where every carbon has an alcohol group, meaning it doesn't form a closed ring. At the very top is the <mark>flavin group</mark>, a complex ring structure with a conjugated double-bond system. That flavin ring is the active business end of the molecule where the electrons actually go.",
    "ei_percent": 85,
    "ei_reasoning": "Introduces FAD's structure and origins, setting up its redox capabilities."
  },
  {
    "slide_number": 28,
    "title": "FAD Redox Chemistry",
    "narrative": "Because of that conjugated double-bond system in the flavin ring, oxidized FAD absorbs light and appears strongly <mark>yellow</mark>. When FAD does its job as an electron carrier, it accepts a <mark>hydride ion</mark> (a hydrogen atom with two electrons) plus an extra proton.\n\nWhen those electrons dump into the flavin ring, they break up the conjugated double-bond system. The molecule is now reduced, becoming <mark>FADH_2</mark>. Because the double bonds are reconfigured, the molecule loses its color entirely. So, if you're watching this reaction in a test tube, you can literally see the FAD shifting from yellow to colorless as it picks up electrons. It's a built-in visual indicator of oxidation state.",
    "ei_percent": 90,
    "ei_reasoning": "Explains the mechanism of FAD reduction and provides a concrete visual anchor (color change)."
  },
  {
    "slide_number": 32,
    "title": "Lipoic Acid",
    "narrative": "The last cofactor on our list is <mark>lipoic acid</mark>. Unlike the others, it doesn't have a handy abbreviation, and it functions as a sort of swinging arm that carries both electrons and carbon groups.\n\nThe active part of lipoic acid is a <mark>disulfide bond</mark> at the end of a carbon chain. You've seen disulfide bonds before holding proteins together. Here, that bond acts as an electron trap. In its oxidized state, the sulfur atoms are bound to each other. When lipoic acid gets reduced, it accepts a hydride transfer, breaking the sulfur-sulfur bond and leaving two separate, reduced thiol (-SH) groups. It cycles back and forth between this closed ring and open-chain state as it moves electrons around.",
    "ei_percent": 85,
    "ei_reasoning": "Details the unique dual-role of lipoic acid and its structural mechanism."
  },
  {
    "slide_number": 35,
    "title": "The PDH Complex",
    "narrative": "So we have this complex reaction turning pyruvate into acetyl-CoA, and we have five distinct cofactors required to make it happen. The cell doesn't just toss pyruvate and five cofactors into the mitochondrial matrix and hope they randomly bump into each other in the right order. Instead, it permanently attaches the enzymes and cofactors into a massive molecular machine called the <mark>pyruvate dehydrogenase complex</mark>, or <mark>PDH</mark> (sometimes written as PDC).\n\nThis complex sits right on the matrix side of the inner mitochondrial membrane. It is a sprawling, beautiful assembly of multiple protein subunits all locked together into a geometric structure. By physically tethering the enzymes into one giant complex, the cell completely eliminates diffusion time. The intermediate products never float away into the matrix. The molecule being processed is handed directly from one active site to the next, like a car chassis moving down a factory assembly line. This phenomenon—substrate channeling—makes the reaction incredibly fast and prevents any of the unstable intermediates from reacting with other things in the cell.",
    "ei_percent": 95,
    "ei_reasoning": "Introduces the macromolecular assembly that executes the reaction and explains the kinetic advantage of substrate channeling."
  },
  {
    "slide_number": 38,
    "title": "PDH Subunits",
    "narrative": "The PDH complex is built from three distinct types of enzyme subunits, creatively named <mark>E1</mark>, <mark>E2</mark>, and <mark>E3</mark>. Each subunit has a specific job and is permanently bound to one of our cofactors.\n\nE1 is the pyruvate dehydrogenase subunit, and it holds onto the thiamine pyrophosphate (TPP$^+$). E2 is the transacetylase subunit, and it's covalently attached to the lipoic acid. E3 is the dehydrogenase subunit, and it holds the FAD. The other two cofactors—NAD$^+$ and Coenzyme A—aren't permanently attached; they float in, do their job, and float away with their new cargo.",
    "ei_percent": 90,
    "ei_reasoning": "Maps the specific cofactors to their respective structural subunits within the complex."
  },
  {
    "slide_number": 40,
    "title": "E1 Mechanism Initiation",
    "narrative": "Let's look at how this assembly line actually starts. The whole process kicks off at the E1 subunit. The TPP$^+$ cofactor sitting in the E1 active site reaches out and attacks the pyruvate molecule.\n\nJust like we saw in ethanol fermentation, the TPP$^+$ catalyzes an <mark>alpha decarboxylation</mark>. It rips the carboxyl group off the pyruvate, releasing our first molecule of CO2. What's left attached to the TPP$^+$ is an activated two-carbon intermediate. If this were fermentation, we'd just pop it off as acetaldehyde. But here, we need to oxidize it. So instead of letting it go, E1 prepares to hand this two-carbon group directly over to the lipoic acid on the E2 subunit.\n\nThe lecture cuts off right as this handoff is about to happen; the prof continues the mechanism next session.",
    "ei_percent": 90,
    "ei_reasoning": "Walks through the first chemical step of the mechanism and provides an honest closing transition."
  }
];
