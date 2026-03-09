"""Upload learning HTML content to S3."""
import boto3
import json

s3 = boto3.client("s3", region_name="us-east-1")
BUCKET = "krishimandal-data-116981771682"

CONTENTS = {
    "ipm_kharif_crops": {
        "title": "Integrated Pest Management (IPM) for Kharif Crops",
        "body": """<h1>Integrated Pest Management (IPM) for Kharif Crops</h1>
<h2>What is IPM?</h2>
<p>IPM is a holistic approach combining multiple strategies to control pests while minimizing economic, health, and environmental risks. It prioritizes prevention and uses chemical controls only as a last resort.</p>
<h2>Key Kharif Pests</h2>
<table border="1" cellpadding="8" style="border-collapse:collapse;width:100%">
<tr><th>Crop</th><th>Major Pests</th><th>IPM Strategy</th></tr>
<tr><td>Rice</td><td>Stem borer, BPH, Leaf folder</td><td>Pheromone traps, Trichogramma release, Neem spray</td></tr>
<tr><td>Cotton</td><td>Bollworm, Whitefly, Jassids</td><td>Bt cotton, Yellow sticky traps, Neem oil</td></tr>
<tr><td>Soybean</td><td>Girdle beetle, Defoliators</td><td>Deep ploughing, Light traps, Need-based spraying</td></tr>
<tr><td>Maize</td><td>Fall armyworm, Stem borer</td><td>Early sowing, Trichogramma, Mechanical removal</td></tr>
</table>
<h2>Step-by-Step IPM Protocol</h2>
<ol>
<li><strong>Prevention:</strong> Use resistant varieties, proper spacing, healthy seeds</li>
<li><strong>Monitoring:</strong> Weekly field scouting, pheromone traps, light traps</li>
<li><strong>Biological Control:</strong> Release Trichogramma (50,000/ha), use NPV for Helicoverpa</li>
<li><strong>Botanical Pesticides:</strong> Neem oil (5ml/L), NSKE 5% spray</li>
<li><strong>Chemical Control (last resort):</strong> Only when ETL is crossed, rotate chemicals</li>
</ol>
<h2>Economic Threshold Levels (ETL)</h2>
<ul>
<li>Rice stem borer: 5% dead hearts or 2% white ears</li>
<li>Cotton bollworm: 1 larva per plant</li>
<li>Soybean defoliator: 25% defoliation in vegetative stage</li>
</ul>
<h2>Banned Pesticides</h2>
<p style="color:red;font-weight:bold">DDT, Endosulfan, Monocrotophos, Methyl Parathion, Phorate (granular)</p>
<p><em>Source: ICAR Technical Bulletin No. 45, Directorate of Plant Protection</em></p>""",
    },
    "zero_budget_farming": {
        "title": "Zero Budget Natural Farming - Subhash Palekar Method",
        "body": """<h1>Zero Budget Natural Farming (ZBNF)</h1>
<h2>Developed by Padma Shri Subhash Palekar</h2>
<h2>Four Pillars of ZBNF</h2>
<h3>1. Jeevamrutha</h3>
<p><strong>Recipe:</strong> 200L water + 10kg fresh cow dung + 5-10L cow urine + 2kg jaggery + 2kg pulse flour + handful of soil. Ferment for 48 hours.</p>
<p><strong>Application:</strong> 200L per acre every 15 days through irrigation.</p>
<h3>2. Bijamrutha</h3>
<p><strong>Recipe:</strong> 20L water + 5kg cow dung + 5L cow urine + 50g lime + handful of bund soil. Use within 48 hours.</p>
<h3>3. Acchadana - Mulching</h3>
<ul><li>Soil mulch, Straw mulch (3-4 inches), Live mulch (intercrop with legumes)</li></ul>
<h3>4. Whapasa - Moisture Management</h3>
<p>Maintain soil at field capacity. Use alternate wetting and drying.</p>
<h2>Panchagavya</h2>
<p>Cow dung 7kg + cow urine 3L + milk 2L + curd 2L + ghee 1kg + sugarcane juice 3L + coconut water 3L + ripe banana 12 nos. Ferment 15 days. Use 3% spray every 15 days.</p>
<h2>Expected Benefits</h2>
<ul><li>Zero input cost after 3 years</li><li>Organic premium: 20-40% higher prices</li><li>Improved soil biology</li><li>NPOP certification eligible</li></ul>
<p><em>Source: ZBNF Training Manual, AP Community Managed Natural Farming</em></p>""",
    },
    "drip_irrigation_guide": {
        "title": "Drip Irrigation Setup Guide for Small Farms",
        "body": """<h1>Drip Irrigation Setup Guide for Small Farms</h1>
<h2>Why Drip?</h2>
<ul><li>Saves 30-50% water</li><li>Increases yield 20-30%</li><li>90%+ water use efficiency</li><li>Government subsidy: 55-70%</li></ul>
<h2>System Components</h2>
<table border="1" cellpadding="8" style="border-collapse:collapse;width:100%">
<tr><th>Component</th><th>Purpose</th><th>Cost (1 acre)</th></tr>
<tr><td>Pump + source</td><td>Supply at 1-2 kg/cm2</td><td>Rs 5,000-15,000</td></tr>
<tr><td>Sand/Disc filter</td><td>Remove particles</td><td>Rs 2,000-5,000</td></tr>
<tr><td>Main line (63mm PVC)</td><td>Source to field</td><td>Rs 3,000-5,000</td></tr>
<tr><td>Sub-main (40mm)</td><td>Distribute to laterals</td><td>Rs 2,000-3,000</td></tr>
<tr><td>Laterals (16mm LLDPE)</td><td>Along crop rows</td><td>Rs 8,000-12,000</td></tr>
<tr><td>Drippers (2-8 LPH)</td><td>Water to root zone</td><td>Rs 3,000-5,000</td></tr>
</table>
<h2>Dripper Spacing</h2>
<ul><li>Vegetables: 30-40 cm, 2-4 LPH</li><li>Sugarcane: 40-60 cm, 4 LPH</li><li>Fruit trees: 2-4 drippers/tree, 8 LPH</li></ul>
<h2>Maintenance</h2>
<ol><li>Flush laterals monthly</li><li>Clean filters weekly</li><li>Check clogged drippers</li><li>Acid treatment every 3 months</li></ol>
<p><em>Source: IARI Extension Bulletin - Micro-Irrigation for Indian Agriculture</em></p>""",
    },
    "soil_health_card": {
        "title": "Soil Health Card - How to Read and Act",
        "body": """<h1>Soil Health Card Guide</h1>
<h2>Key Parameters</h2>
<table border="1" cellpadding="8" style="border-collapse:collapse;width:100%">
<tr><th>Parameter</th><th>Ideal Range</th><th>If Low</th><th>If High</th></tr>
<tr><td>pH</td><td>6.0-7.5</td><td>Apply lime 2-4 t/ha</td><td>Apply gypsum/sulfur</td></tr>
<tr><td>Organic Carbon</td><td>&gt;0.75%</td><td>Add FYM 5-10 t/ha</td><td>Maintain</td></tr>
<tr><td>Nitrogen</td><td>280-560 kg/ha</td><td>Apply urea/DAP</td><td>Reduce N fertiliser</td></tr>
<tr><td>Phosphorus</td><td>22-56 kg/ha</td><td>Apply SSP or DAP</td><td>Skip P this season</td></tr>
<tr><td>Potassium</td><td>135-335 kg/ha</td><td>Apply MOP</td><td>Skip K this season</td></tr>
<tr><td>Zinc</td><td>&gt;0.6 ppm</td><td>Zinc Sulphate 25 kg/ha</td><td>Normal</td></tr>
</table>
<h2>How to Improve Soil</h2>
<ul><li>Add FYM/compost every season</li><li>Crop rotation with legumes</li><li>Green manuring with Dhaincha</li><li>Minimum/zero tillage</li><li>Bio-fertilisers: Rhizobium, PSB, Azotobacter</li></ul>
<p><em>Source: Soil Health Card Scheme - Dept. of Agriculture</em></p>""",
    },
    "rainwater_harvesting": {
        "title": "Rainwater Harvesting - Farm Pond Construction",
        "body": """<h1>Farm Pond Construction Guide</h1>
<h2>Why Farm Ponds?</h2>
<ul><li>30mx30mx3m pond stores ~27 lakh litres</li><li>Supplemental irrigation for 2-3 critical waterings</li><li>Groundwater recharge</li><li>Fisheries income</li></ul>
<h2>Government Subsidies</h2>
<table border="1" cellpadding="8" style="border-collapse:collapse;width:100%">
<tr><th>Scheme</th><th>Subsidy</th></tr>
<tr><td>MGNREGA</td><td>100% labour cost</td></tr>
<tr><td>PMKSY-WDC</td><td>Up to 50%</td></tr>
<tr><td>State schemes</td><td>50-90%</td></tr>
</table>
<h2>Construction Steps</h2>
<ol><li>Site selection: lowest point, clay soil</li><li>Trapezoidal cross-section, slope 1:1.5</li><li>Excavation via JCB or MGNREGA</li><li>Silpaulin 250 GSM lining</li><li>Inlet channels + overflow outlet</li><li>Safety fencing</li></ol>
<h2>Crop Water Requirements</h2>
<ul><li>Wheat: 450mm</li><li>Cotton: 700mm</li><li>Sugarcane: 1800mm</li><li>Soybean: 450-500mm</li></ul>
<p><em>Source: CWRDM & ICAR - Water Management in Rainfed Agriculture</em></p>""",
    },
    "pm_kisan_guide": {
        "title": "PM-KISAN Registration Step-by-Step",
        "body": """<h1>PM-KISAN Samman Nidhi Guide</h1>
<h2>Benefits</h2>
<p>Rs 6,000/year in 3 instalments of Rs 2,000 directly to bank account.</p>
<h2>Eligibility</h2>
<ul><li>All land-holding farmer families</li><li>Both rural and urban</li></ul>
<h2>NOT Eligible</h2>
<ul><li>Income tax payers</li><li>Government employees</li><li>Professionals (doctors, lawyers, CAs)</li><li>Pensioners (Rs 10,000+/month)</li></ul>
<h2>Documents Required</h2>
<ol><li>Aadhaar Card</li><li>Bank account (Aadhaar-linked)</li><li>Land records (Khasra/Khatauni)</li><li>Mobile number</li></ol>
<h2>Registration</h2>
<ol><li>Visit pmkisan.gov.in</li><li>Click New Farmer Registration</li><li>Enter Aadhaar + details</li><li>Submit for verification</li></ol>
<h2>Instalment Schedule</h2>
<ul><li>April-July: Rs 2,000</li><li>August-November: Rs 2,000</li><li>December-March: Rs 2,000</li></ul>
<p><em>Source: PM-KISAN Official Guidelines - Ministry of Agriculture</em></p>""",
    },
    "pmfby_insurance": {
        "title": "PMFBY Crop Insurance - How to Claim",
        "body": """<h1>PMFBY Crop Insurance Guide</h1>
<h2>Premium Rates</h2>
<table border="1" cellpadding="8" style="border-collapse:collapse;width:100%">
<tr><th>Season</th><th>Premium</th><th>Example (SI Rs 50k)</th></tr>
<tr><td>Kharif</td><td>2%</td><td>Rs 1,000</td></tr>
<tr><td>Rabi</td><td>1.5%</td><td>Rs 750</td></tr>
<tr><td>Horticulture</td><td>5%</td><td>Rs 2,500</td></tr>
</table>
<h2>Coverage</h2>
<ul><li>Natural calamities</li><li>Pest/disease attacks</li><li>Post-harvest losses (14 days)</li><li>Prevented sowing</li></ul>
<h2>How to Claim</h2>
<ol><li><strong>Report within 72 hours</strong></li><li>Call 14447 or use Crop Insurance App</li><li>Provide policy number, Aadhaar, photos</li><li>Assessment within 7 days</li><li>Settlement within 2 months</li></ol>
<p><em>Source: PMFBY Operational Guidelines</em></p>""",
    },
    "vermicompost_guide": {
        "title": "Vermicompost Production at Home",
        "body": """<h1>Vermicompost Production Guide</h1>
<h2>Materials</h2>
<ul><li>Earthworms: Eisenia fetida, 1kg/bed</li><li>Cow dung: 500-1000 kg (15-20 days old)</li><li>Crop residue: 500 kg chopped</li><li>Bed: 10ft x 3ft x 2ft</li></ul>
<h2>Process</h2>
<ol><li>Prepare bed (brick/pit 10x3x2 ft)</li><li>Layer 6" cow dung</li><li>Layer 4" chopped residue</li><li>Repeat layers</li><li>Release 1 kg worms (~1000)</li><li>Cover with jute bag</li><li>Water every 2-3 days</li><li>Turn gently every 15 days</li><li>Harvest at 45-60 days</li></ol>
<h2>Application Rates</h2>
<ul><li>Field crops: 2-3 t/ha</li><li>Vegetables: 3-5 t/ha</li><li>Fruit trees: 5-10 kg/tree</li></ul>
<h2>Economics</h2>
<p>1 bed = 600-800 kg/cycle. Price: Rs 8-15/kg. 5 beds = Rs 30,000-50,000/year.</p>
<p><em>Source: ICAR - Vermicompost Production Technology</em></p>""",
    },
    "neem_biopesticide": {
        "title": "Neem-based Bio-Pesticide Preparation",
        "body": """<h1>Neem Bio-Pesticide Guide</h1>
<h2>1. NSKE 5% (Most Effective)</h2>
<ol><li>Collect neem kernels, dry in shade</li><li>Pound 50g into powder</li><li>Soak in 1L water overnight</li><li>Filter through muslin</li><li>Add 1ml liquid soap</li><li>Spray immediately</li></ol>
<p><strong>For:</strong> Aphids, whitefly, jassids, caterpillars</p>
<h2>2. Neem Oil Spray (2-3%)</h2>
<ol><li>20-30ml neem oil per litre water</li><li>Add 5ml liquid soap</li><li>Shake well, spray in evening</li></ol>
<p><strong>For:</strong> Mites, scales, mealybugs, powdery mildew</p>
<h2>3. Neem Cake</h2>
<ul><li>250-500 kg/ha as soil amendment</li><li>Controls nematodes, white grubs, termites</li></ul>
<h2>Schedule</h2>
<ul><li>Preventive: every 15 days</li><li>Curative: every 7 days</li><li>Best time: evening after 4 PM</li></ul>
<p><em>Source: ICAR-NBAIR - Bio-pesticide Formulations</em></p>""",
    },
    "micro_irrigation_subsidy": {
        "title": "Micro-Irrigation Subsidy Application Guide",
        "body": """<h1>Micro-Irrigation Subsidy Guide</h1>
<h2>Schemes Available</h2>
<h3>PMKSY - Per Drop More Crop</h3>
<ul><li>55% for small/marginal farmers, 45% for others</li><li>Covers drip, sprinkler, micro-sprinkler</li></ul>
<h3>State Top-up Subsidies</h3>
<table border="1" cellpadding="8" style="border-collapse:collapse;width:100%">
<tr><th>State</th><th>Additional</th><th>Total</th></tr>
<tr><td>Maharashtra</td><td>25%</td><td>80%</td></tr>
<tr><td>Gujarat</td><td>25%</td><td>80%</td></tr>
<tr><td>Rajasthan</td><td>20%</td><td>75%</td></tr>
<tr><td>Karnataka</td><td>25%</td><td>80%</td></tr>
<tr><td>Andhra Pradesh</td><td>25-35%</td><td>90%</td></tr>
</table>
<h2>Application Process</h2>
<ol><li>Register on state agriculture portal</li><li>Upload: Aadhaar, 7/12 extract, bank passbook</li><li>Select system + approved vendor</li><li>Get pre-sanction approval</li><li>Purchase and install</li><li>Submit photos and bills</li><li>Inspection by Agri Officer</li><li>Subsidy credited (30-60 days)</li></ol>
<p><em>Source: PMKSY Guidelines - Ministry of Agriculture</em></p>""",
    },
}

STYLE = """<style>
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; color: #333; }
h1 { color: #2D5F2E; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
h2 { color: #388E3C; margin-top: 24px; }
h3 { color: #43A047; }
table { width: 100%; margin: 16px 0; }
th { background: #E8F5E9; color: #2D5F2E; text-align: left; }
td, th { padding: 8px 12px; border: 1px solid #C8E6C9; }
ul, ol { padding-left: 24px; }
li { margin-bottom: 6px; }
em { color: #666; font-size: 0.9em; }
</style>"""

for key, c in CONTENTS.items():
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{c['title']}</title>{STYLE}</head>
<body>{c['body']}
<hr><p style="text-align:center;color:#888;font-size:0.85em">KrishiMandal Learning Platform</p>
</body></html>"""

    s3.put_object(
        Bucket=BUCKET,
        Key=f"learning/{key}.html",
        Body=html.encode("utf-8"),
        ContentType="text/html",
    )
    print(f"Uploaded learning/{key}.html")

print("Done!")
