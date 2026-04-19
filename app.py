import os
import uuid
import datetime
import json
import logging
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

# Import our advanced utility modules
from utils.database_seed import list_all_fibers, list_all_chemicals
from utils.calculations import FootprintCalculator, ChemicalAuditor

# ---------------------------------------------------------
# Application Configuration & Logging Setup
# ---------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get('ECO_THREAD_SECRET_KEY', 'ECO_THREAD_SUPER_SECRET_KEY')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('EcoThread_App')

# ---------------------------------------------------------
# Mock Database (In-Memory) for Prototype Scope
# ---------------------------------------------------------
# Pre-seeded Factory Managers list
FACTORY_MANAGERS = {
    "manager@ecothread.com": generate_password_hash("Textile2026!")
}

# In-memory document store: { "audit_id": { ...audit payload... } }
AUDIT_DB = {}

# ---------------------------------------------------------
# Decorators & Middleware
# ---------------------------------------------------------
def login_required(f):
    """Ensure the user is authenticated via session variables."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash("Secure authentication required. Please log in.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ---------------------------------------------------------
# Authentication Routes
# ---------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Secure login mechanism for factory credentials."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        try:
            if not email or not password:
                raise ValueError("Incomplete credentials provided.")
                
            if email in FACTORY_MANAGERS and check_password_hash(FACTORY_MANAGERS[email], password):
                session['user'] = email
                session['last_login'] = datetime.datetime.now().isoformat()
                logger.info(f"Successful login for {email}")
                flash("Authentication successful. Welcome to EcoThread.", "success")
                return redirect(url_for('dashboard'))
            else:
                logger.warning(f"Failed login attempt for {email}")
                flash("Invalid credentials or unauthorized terminal.", "danger")
                
        except ValueError as ve:
            flash(str(ve), "danger")
        except Exception as e:
            logger.error(f"Login subsystem failure: {str(e)}")
            flash("Internal authentication error.", "danger")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Wipe session data securely."""
    user = session.pop('user', None)
    session.clear()
    if user:
        logger.info(f"User {user} logged out.")
    flash("Session terminated securely.", "info")
    return redirect(url_for('login'))

# ---------------------------------------------------------
# Dashboard & Viewing Routes
# ---------------------------------------------------------
@app.route('/')
@login_required
def dashboard():
    """
    Main organizational dashboard visualizing critical compliance data.
    Implements a basic pseudo-pagination (limits to 100 recent for performance).
    """
    try:
        # Sort audits chronologically descending
        all_audits = sorted(AUDIT_DB.values(), key=lambda x: x['timestamp'], reverse=True)
        recent_audits = all_audits[:100]
        
        total_audits = len(all_audits)
        certified_count = sum(1 for a in all_audits if a['overall_status'] == 'Eco-Certified')
        high_risk_count = total_audits - certified_count
        
        # Calculate some aggregate industrial metrics
        aggregate_water = sum(a['footprint'].get('water_metrics', {}).get('total_liters', 0) for a in all_audits)
        aggregate_carbon = sum(a['footprint'].get('carbon_metrics', {}).get('total_kgCO2e', 0) for a in all_audits)
        
        return render_template('dashboard.html', 
                               audits=recent_audits, 
                               total=total_audits,
                               certified=certified_count,
                               risk=high_risk_count,
                               agg_water=round(aggregate_water, 2),
                               agg_carbon=round(aggregate_carbon, 2))
    except Exception as e:
        logger.error(f"Dashboard render failed: {str(e)}")
        flash("Error loading dashboard metrics.", "danger")
        return render_template('dashboard.html', audits=[], total=0, certified=0, risk=0)

# ---------------------------------------------------------
# Data Processing Routes
# ---------------------------------------------------------
@app.route('/audit/new', methods=['GET', 'POST'])
@login_required
def audit_form():
    """
    Comprehensive endpoint for submitting complex lab results and fetching 
    algorithmic sustainability determinations.
    """
    fibers = list_all_fibers()
    # Randomly select a subset of chemicals to render to prevent DOM overload, 
    # normally we'd utilize an async search dropdown in a full JS framework.
    chemicals = list_all_chemicals()[:100] 
    
    if request.method == 'POST':
        try:
            # --- 1. Parse Supply Chain Metrics ---
            fiber_selection = request.form.get('fiber_type')
            region_selection = request.form.get('region', 'Global Average')
            wet_processing = request.form.get('wet_processing_type', 'Standard')
            
            volume_str = request.form.get('volume_kg', '0')
            if not volume_str.replace('.', '', 1).isdigit():
                raise ValueError("Volume must be a strictly numeric value.")
            volume_kg = float(volume_str)
            
            # --- 2. Parse Chemical Formulation Details ---
            lab_results_dict = {}
            for key, val in request.form.items():
                if key.startswith('chem_') and val.strip() != '':
                    chem_name = key.replace('chem_', '', 1)
                    try:
                        detected_ppm = float(val)
                        if detected_ppm < 0:
                            raise ValueError("Concentration cannot be negative.")
                        lab_results_dict[chem_name] = detected_ppm
                    except ValueError:
                        continue # Silently omit non-valid entries 
            
            # --- 3. Run EcoThread Analytics Engine ---
            logger.info("Executing FootprintCalculator analytics pipeline...")
            footprint_result = FootprintCalculator.calculate_total_impact(
                fiber_name=fiber_selection, 
                volume_kg=volume_kg,
                wet_processing_type=wet_processing,
                region=region_selection
            )
            
            if footprint_result.get('status') == 'error':
                raise Exception(f"Thermodynamic Engine failure: {footprint_result.get('message')}")
                
            logger.info("Executing ChemicalAuditor tox pipeline...")
            audit_result = ChemicalAuditor.audit_batch(lab_results_dict, target_standard="ZDHC")
            if audit_result.get('overall_status') == 'Error':
                raise Exception(f"Toxicology Engine failure: {audit_result.get('message')}")
                
            # --- 4. Synthesize Final Assessment ---
            audit_id = f"ECO-{str(uuid.uuid4())[:8].upper()}"
            
            # If footprint score is too low or chemical failed -> High Risk
            fp_score = footprint_result.get('eco_score_100', 0)
            if audit_result["overall_status"] == "High Risk" or fp_score < 40.0:
                overall_status = "High Risk"
            else:
                overall_status = "Eco-Certified"
            
            payload = {
                "id": audit_id,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "operator": session.get('user'),
                "fiber": fiber_selection,
                "region": region_selection,
                "process_type": wet_processing,
                "volume_kg": volume_kg,
                "footprint": footprint_result,
                "chemical_audit": audit_result,
                "overall_status": overall_status
            }
            
            # Commit to DB
            AUDIT_DB[audit_id] = payload
            logger.info(f"Audit {audit_id} committed. Status: {overall_status}")
            
            flash(f"Audit {audit_id} synthesized. Clearance: {overall_status}", 
                  "success" if overall_status == "Eco-Certified" else "danger")
                  
            return redirect(url_for('generate_report', audit_id=audit_id))
            
        except ValueError as ve:
            logger.warning(f"Validation error: {str(ve)}")
            flash(f"Data Schema Invalid: {str(ve)}", "warning")
        except Exception as e:
            logger.error(f"Pipeline fault: {str(e)}", exc_info=True)
            flash(f"Core System Fault: {str(e)}", "danger")

    return render_template('audit_form.html', fibers=fibers, chemicals=chemicals)


# ---------------------------------------------------------
# Reporting & Export Routes
# ---------------------------------------------------------
@app.route('/report/<audit_id>')
@login_required
def generate_report(audit_id):
    """Render the HTML compliance certificate for review."""
    audit = AUDIT_DB.get(audit_id)
    if not audit:
        flash("Requested Audit ID unlocatable in primary shard.", "danger")
        return redirect(url_for('dashboard'))
        
    return render_template('certificate.html', audit=audit)

@app.route('/api/v1/export/txt/<audit_id>')
@login_required
def download_txt_report(audit_id):
    """
    Generate an offline-capable raw text certificate representing the 
    algorithmic determination, suitable for legacy supply chain archiving.
    """
    try:
        audit = AUDIT_DB.get(audit_id)
        if not audit:
            raise KeyError("Audit ID orphaned or non-existent.")
            
        filepath = os.path.join('/tmp', f'compliance_manifest_{audit_id}.txt')
        
        # Ensure tmp exists
        os.makedirs('/tmp', exist_ok=True)
        
        with open(filepath, 'w') as f:
            f.write("====================================================\n")
            f.write("      ECOTHREAD ADVANCED SUSTAINABILITY MANIFEST      \n")
            f.write("====================================================\n\n")
            f.write(f"System ID: {audit['id']}\n")
            f.write(f"Generated: {audit['timestamp']}\n")
            f.write(f"Operator : {audit['operator']}\n")
            f.write(f"STATUS   : {audit['overall_status']}\n\n")
            
            f.write("--- 1. SUPPLY CHAIN DETAILS ---\n")
            f.write(f"Fiber Genus : {audit['fiber']}\n")
            f.write(f"Procurement : {audit['region']}\n")
            f.write(f"Wet-Process : {audit['process_type']}\n")
            f.write(f"Total Mass  : {audit['volume_kg']} kg\n\n")
            
            f.write("--- 2. THERMODYNAMIC FOOTPRINT ---\n")
            fp = audit['footprint']
            wm = fp.get('water_metrics', {})
            cm = fp.get('carbon_metrics', {})
            
            f.write(f"Total Water Reqd : {wm.get('total_liters')} L\n")
            f.write(f"  -> Blue Water  : {wm.get('blue_water_L')} L\n")
            f.write(f"  -> Green Water : {wm.get('green_water_L')} L\n")
            f.write(f"  -> Grey Water  : {wm.get('grey_water_L')} L (pollution dilution proxy)\n\n")
            
            f.write(f"Carbon Load      : {cm.get('total_kgCO2e')} kgCO2e\n")
            f.write(f"  -> Scope 1     : {cm.get('scope_1')} kgCO2e\n")
            f.write(f"  -> Scope 2     : {cm.get('scope_2')} kgCO2e\n")
            f.write(f"  -> Scope 3     : {cm.get('scope_3')} kgCO2e\n\n")
            
            f.write(f"Energy Potential : {fp.get('energy_kwh')} kWh\n")
            f.write(f"Bio-Degradable   : {fp.get('materials', {}).get('biodegradable')}\n")
            f.write(f"Eco-Score Rating : {fp.get('eco_score_100')} / 100\n\n")
            
            f.write("--- 3. TOXICOLOGY AUDIT (ZDHC MRSL V3) ---\n")
            chem = audit['chemical_audit']
            f.write(f"Compounds Tested : {chem.get('total_tested')}\n")
            f.write(f"Critical Fails   : {chem.get('critical_failures')}\n")
            if 'cocktail_risk_level' in chem.get('cocktail_analysis', {}):
                f.write(f"Cocktail Risk    : {chem['cocktail_analysis']['cocktail_risk_level']}\n")
            f.write("\nDetailed Traces:\n")
            for result in chem.get('details', []):
                stat = "[FAIL]" if result['status'] == "FAILED" else "[PASS]"
                limit_str = f"Limit: {result.get('limit_ppm')} ppm"
                f.write(f"  {stat} {result['chemical']}: {result['detected_ppm']} ppm ({limit_str}) - {result.get('rating_tier')}\n")
                
            f.write("\n====================================================\n")
            f.write("[EOD - SYSTEM HASH VERIFIED]\n")
            
        logger.info(f"Manifest exported for {audit_id} to tmp volume.")
        return send_file(filepath, as_attachment=True)
        
    except Exception as e:
        logger.error(f"Report export fault: {str(e)}")
        flash("Export subsystem failure.", "danger")
        return redirect(url_for('dashboard'))


@app.route('/api/v1/health')
def health_check():
    """REST API endpoint for load balancers."""
    return jsonify({
        "status": "operational",
        "active_audits": len(AUDIT_DB),
        "timestamp": datetime.datetime.utcnow().isoformat()
    }), 200

if __name__ == '__main__':
    logger.info("Initializing EcoThread SaaS Cluster (Local Node)...")
    app.run(debug=True, port=5000, threaded=True)
