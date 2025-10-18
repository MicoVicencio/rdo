from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os
import random
import textwrap

# List of all available courses (kept from original)
courses = [
    "Bachelor of Science in Business Administration (BSBA)",
    "Bachelor of Science in Office Administration (BSOA)",
    "Bachelor of Science in Computer Science (BSCS)",
    "Bachelor of Secondary Education (BSED)",
    "Bachelor of Elementary Education (BEED)",
    "Bachelor of Arts in Religious Education (ABREED)"
]

# A pool of years to randomly assign (UPDATED to 2018-2024)
year_pool = [
    "March 2018", "March 2019", "March 2020", "March 2021", "March 2022",
    "March 2023", "March 2024"
]

# Dummy names pool (kept from original)
names_pool = [
    "Santos, Juan", "Reyes, Maria", "Cruz, Pedro", "Dela Cruz, Ana",
    "Garcia, Jose", "Mendoza, Carla", "Lopez, Mark", "Torres, Liza",
    "Fernandez, Paul", "Ramos, Nicole", "Vicente, Carlo", "Domingo, Karen",
    "Flores, Miguel", "Rivera, Angela", "Castro, John", "Diaz, Sophia",
    "Navarro, Kevin", "Gutierrez, Bella", "Jimenez, Marco", "Santiago, Rose",
    "Aquino, James", "Padilla, Erika", "Marquez, Ivan", "Villanueva, Ella",
    "Ortiz, Daniel", "Pascual, Hannah", "Bautista, Ryan", "Salazar, Chloe",
    "Silva, Patrick", "Morales, Julia"
]

# --- 60 COURSE-SPECIFIC THESIS DATA ENTRIES (10 per course) ---

thesis_data = []

# 1. BSBA (Business Administration) - Focus: Management, Finance, Marketing
bsba_titles = [
    "THE IMPACT OF SOCIAL MEDIA MARKETING ON SMALL AND MEDIUM ENTERPRISES' SALES PERFORMANCE",
    "ANALYSIS OF FINANCIAL LITERACY AND INVESTMENT DECISIONS AMONG YOUNG PROFESSIONALS",
    "IMPLEMENTATION OF TOTAL QUALITY MANAGEMENT (TQM) IN THE SERVICE SECTOR: A CASE STUDY",
    "FACTORS AFFECTING EMPLOYEE RETENTION IN THE BPO INDUSTRY IN METRO MANILA",
    "THE ROLE OF E-COMMERCE ADOPTION IN THE COMPETITIVENESS OF TRADITIONAL RETAIL STORES",
    "ASSESSMENT OF RISK MANAGEMENT STRATEGIES IN LOCAL COOPERATIVE BANKS",
    "CONSUMER PERCEPTION AND ATTITUDE TOWARDS SUSTAINABLE AND ETHICAL BUSINESS PRACTICES",
    "DETERMINANTS OF SUCCESS FOR START-UP COMPANIES IN THE PHILIPPINES: A QUALITATIVE STUDY",
    "AN EVALUATION OF SUPPLY CHAIN RESILIENCE AMIDST GLOBAL ECONOMIC DISRUPTIONS",
    "THE EFFECT OF LEADERSHIP STYLES ON ORGANIZATIONAL COMMITMENT AMONG EMPLOYEES"
]

# 2. BSOA (Office Administration) - Focus: Office Systems, Records, Technology
bsoa_titles = [
    "EFFICIENCY ASSESSMENT OF DIGITAL RECORD MANAGEMENT SYSTEMS IN A GOVERNMENT OFFICE",
    "THE EFFECTIVENESS OF VIRTUAL ASSISTANTS IN MANAGING EXECUTIVE ADMINISTRATIVE TASKS",
    "DEVELOPMENT OF A STANDARDIZED FILING AND RETRIEVAL SYSTEM FOR LEGAL DOCUMENTS",
    "ANALYSIS OF ERGONOMIC FACTORS AND THEIR INFLUENCE ON OFFICE WORKER PRODUCTIVITY",
    "IMPLEMENTATION OF AN ONLINE APPOINTMENT AND SCHEDULING SYSTEM FOR OPTIMAL OFFICE WORKFLOW",
    "EVALUATING DATA SECURITY PROTOCOLS FOR CONFIDENTIAL OFFICE INFORMATION",
    "COMPETENCIES REQUIRED FOR THE MODERN OFFICE ADMINISTRATOR IN A HYBRID WORK ENVIRONMENT",
    "STUDY ON THE ADOPTION OF CLOUD-BASED COLLABORATION TOOLS IN ACADEMIC ADMINISTRATION",
    "IMPACT OF AUTOMATION ON ROUTINE OFFICE PROCEDURES IN THE FINANCIAL SECTOR",
    "PERCEPTION OF OFFICE STAFF ON THE EFFICACY OF PAPERLESS COMMUNICATION POLICIES"
]

# 3. BSCS (Computer Science) - Focus: Development, Algorithms, AI, IOT
bscs_titles = [
    "DEVELOPMENT OF A MACHINE LEARNING MODEL FOR PREDICTING STUDENT ACADEMIC FAILURE",
    "DESIGN AND IMPLEMENTATION OF A SECURE DECENTRALIZED VOTING SYSTEM USING BLOCKCHAIN",
    "REAL-TIME OBJECT DETECTION AND TRACKING SYSTEM FOR TRAFFIC MONITORING",
    "COMPARATIVE ANALYSIS OF PATHFINDING ALGORITHMS IN LARGE-SCALE VIRTUAL ENVIRONMENTS",
    "CONSTRUCTION OF AN IOT-BASED SOIL MOISTURE AND PH LEVEL MONITORING SYSTEM FOR AGRICULTURE",
    "A NATURAL LANGUAGE PROCESSING APPROACH FOR AUTOMATED ESSAY GRADING",
    "CREATION OF A MOBILE APPLICATION FOR DISASTER RESPONSE AND RESOURCE ALLOCATION",
    "EXPLORATION OF GRAPH NEURAL NETWORKS FOR SOCIAL NETWORK COMMUNITY DETECTION",
    "DEVELOPMENT OF A SECURE CHAT APPLICATION UTILIZING END-TO-END ENCRYPTION",
    "IMPLEMENTATION OF COMPUTER VISION FOR QUALITY CONTROL IN MANUFACTURING PROCESSES"
]

# 4. BSED (Secondary Education) - Focus: Teaching Methods, Curriculum, Adolescent Learning
bsed_titles = [
    "EFFECTIVENESS OF BLENDED LEARNING IN TEACHING COMPLEX MATHEMATICAL CONCEPTS TO JUNIOR HIGH SCHOOL STUDENTS",
    "IMPACT OF PROJECT-BASED LEARNING ON THE CRITICAL THINKING SKILLS OF SENIOR HIGH SCHOOL STUDENTS",
    "TEACHERS' PERCEPTIONS ON THE INTEGRATION OF LOCAL HISTORY IN THE SOCIAL STUDIES CURRICULUM",
    "CHALLENGES AND STRATEGIES IN TEACHING SCIENCE IN MULTIGRADE SECONDARY CLASSROOMS",
    "A STUDY ON THE RELATIONSHIP BETWEEN ADOLESCENT SELF-EFFICACY AND ACADEMIC PERFORMANCE IN ENGLISH",
    "DEVELOPMENT AND VALIDATION OF INSTRUCTIONAL MATERIALS FOR 21ST CENTURY SKILLS IN TECHNOLOGY EDUCATION",
    "INVESTIGATING THE ROLE OF FORMATIVE ASSESSMENT IN IMPROVING STUDENT LEARNING OUTCOMES",
    "ANALYSIS OF TEACHING STYLES AND LEARNER ENGAGEMENT IN DIFFERENT SUBJECT AREAS",
    "EFFECTIVENESS OF DIFFERENTIATED INSTRUCTION IN ADDRESSING LEARNING DIVERSITY AMONG ADOLESCENTS",
    "PREDICTORS OF BURNOUT AMONG SECONDARY SCHOOL TEACHERS IN PUBLIC AND PRIVATE SCHOOLS"
]

# 5. BEED (Elementary Education) - Focus: Early Childhood, Literacy, Pedagogy
beed_titles = [
    "EFFECTIVENESS OF STORYTELLING AS A TOOL FOR ENHANCING LITERACY SKILLS IN GRADE 1 PUPILS",
    "DESIGN AND EVALUATION OF INDIGENOUS GAMES AS TEACHING AIDS IN ELEMENTARY MATHEMATICS",
    "IMPACT OF PARENTAL INVOLVEMENT ON THE ACADEMIC READINESS OF KINDERGARTEN CHILDREN",
    "ASSESSMENT OF TEACHERS' PRACTICES IN PROMOTING SOCIO-EMOTIONAL DEVELOPMENT IN THE EARLY GRADES",
    "EXPLORATION OF PHONOLOGICAL AWARENESS STRATEGIES AMONG GRADE 2 PUPILS WITH READING DIFFICULTIES",
    "THE ROLE OF ART INTEGRATION IN ENHANCING CREATIVITY IN THE ELEMENTARY CLASSROOM",
    "DEVELOPMENT OF A REMEDIAL PROGRAM FOR NUMERACY SKILLS IN LOW-PERFORMING GRADE 3 PUPILS",
    "CHALLENGES OF CLASSROOM MANAGEMENT IN LARGE ELEMENTARY CLASSES AND TEACHERS' COPING MECHANISMS",
    "COMPARATIVE STUDY OF TRADITIONAL VERSUS PLAY-BASED LEARNING APPROACHES IN EARLY CHILDHOOD EDUCATION",
    "EFFECTIVENESS OF USING CONCRETE MANIPULATIVES IN TEACHING FRACTIONS TO GRADE 4 PUPILS"
]

# 6. ABREED (Religious Education) - Focus: Theology, Ethics, Formation
abreed_titles = [
    "THE IMPACT OF CATECHETICAL PROGRAMS ON THE MORAL FORMATION OF COLLEGE STUDENTS",
    "ANALYSIS OF THE ROLE OF SOCIAL MEDIA IN SHAPING THE RELIGIOUS BELIEFS OF THE YOUTH",
    "DEVELOPMENT OF A COMMUNITY-BASED YOUTH EVANGELIZATION PROGRAM USING SERVICE LEARNING",
    "EXPLORATION OF FILIPINO FAMILY VALUES AND THEIR INTERSECTION WITH CATHOLIC SOCIAL TEACHING",
    "A STUDY ON THE SPIRITUAL LEADERSHIP STYLES OF PARISH PRIESTS AND THEIR EFFECT ON CHURCH ATTENDANCE",
    "THEOLOGICAL REFLECTION ON THE ECOLOGICAL CRISIS: A FAITH-BASED RESPONSE",
    "CHALLENGES IN TEACHING RELIGIOUS EDUCATION IN A MULTI-FAITH CLASSROOM SETTING",
    "PERCEPTION OF LAY MINISTERS ON THE EFFECTIVENESS OF ADULT FAITH FORMATION PROGRAMS",
    "ANALYSIS OF THE ETHICAL IMPLICATIONS OF ARTIFICIAL INTELLIGENCE FROM A CHRISTIAN PERSPECTIVE",
    "THE ROLE OF SCHOOL RELIGIOUS EDUCATION IN PROMOTING INTERFAITH DIALOGUE AND HARMONY"
]

# Combine all titles and courses into the final data structure
course_title_map = {
    courses[0]: bsba_titles,
    courses[1]: bsoa_titles,
    courses[2]: bscs_titles,
    courses[3]: bsed_titles,
    courses[4]: beed_titles,
    courses[5]: abreed_titles,
}

# Generate the full list of (title, course, year) tuples
for course, titles in course_title_map.items():
    for title in titles:
        # Assign a random year from the pool to each thesis
        random_year = random.choice(year_pool)
        thesis_data.append((title, course, random_year))


# Output folder
output_dir = "generated_thesis_pdfs"
# Ensure the directory exists
os.makedirs(output_dir, exist_ok=True)

# Function to clean title into a safe filename
def clean_title_for_filename(title, max_length=80):
    # Convert to uppercase and replace common unsafe characters with underscores
    cleaned = title.upper().replace(' ', '_').replace("'", "").replace(',', '').replace(':', '').replace('-', '_').replace('(', '').replace(')', '').replace('.', '')
    # Filter to keep only alphanumeric and underscore characters
    safe_chars = ''.join(c for c in cleaned if c.isalnum() or c == '_')
    # Limit length
    if len(safe_chars) > max_length:
        safe_chars = safe_chars[:max_length]
    return safe_chars

# Generate each PDF
print(f"Generating {len(thesis_data)} course-specific thesis title pages...")

for title, course, year in thesis_data:
    
    # NEW FILENAME LOGIC: Use the cleaned, full title
    filename_base = clean_title_for_filename(title)
    filename = f"{filename_base}.pdf"
    filepath = os.path.join(output_dir, filename)

    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4

    # --- FORMATTING SECTION ---

    # University/College Header (Kept for official top-of-page identification)
    c.setFont("Times-Bold", 18)
    c.drawCentredString(width/2, height - 80, "CAINTA CATHOLIC COLLEGE")
    c.setFont("Times-Roman", 10)
    c.drawCentredString(width/2, height - 95, "A. Bonifacio Ave., Brgy. Sto. Niño, Cainta, Rizal, Philippines")

    # Title (wrap if too long)
    c.setFont("Times-Bold", 14)
    wrapped_title = textwrap.wrap(title.upper(), 50)  # max 50 chars per line
    y = height - 170 # Start position for the main title
    for line in wrapped_title:
        c.drawCentredString(width/2, y, line)
        y -= 20
    y -= 10 # Extra space after title

    # Subtitle Text (Following the requested format)
    c.setFont("Times-Roman", 12)
    subtitle_lines = [
        "",
        "A Thesis",
        "Presented to the Faculty of Cainta Catholic College",
        "Cainta, Rizal",
        "",
        "In Partial Fulfillment of the Requirements for the Degree",
    ]

    for line in subtitle_lines:
        c.drawCentredString(width/2, y, line)
        y -= 20

    # Course Name (Variable)
    c.setFont("Times-BoldItalic", 13)
    c.drawCentredString(width/2, y, course)
    y -= 30

    # Authors Header
    c.setFont("Times-Roman", 12)
    c.drawCentredString(width/2, y, "By:")
    y -= 20

    # Authors (Randomly selected 5 names)
    c.setFont("Times-Roman", 12)
    authors = random.sample(names_pool, 5)
    for author in authors:
        c.drawCentredString(width/2, y, author)
        y -= 20

    # Year
    y -= 40
    c.setFont("Times-Bold", 12)
    c.drawCentredString(width/2, y, year)

    # Save and continue
    c.showPage()
    c.save()

print(f"\n✅ Successfully generated {len(thesis_data)} course-specific PDF files in the '{output_dir}' folder.")
