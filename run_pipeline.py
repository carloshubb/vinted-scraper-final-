"""
Master Pipeline Runner for Vinted Market Intelligence
Runs: Scrape → Process → Calculate KPIs
"""
import subprocess
import sys
import logging
from datetime import datetime
from pathlib import Path

# Setup logging with UTF-8 encoding for Windows compatibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(
            f'pipeline_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
            encoding='utf-8'
        ),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def run_command(command, description):
    """Run a command and handle errors."""
    logger.info("="*70)
    logger.info(f"STEP: {description}")
    logger.info("="*70)
    
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(result.stdout)
        if result.stderr:
            logger.warning(result.stderr)
        logger.info(f"[OK] {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"[FAIL] {description} failed!")
        logger.error(f"Error: {e}")
        logger.error(f"Output: {e.stdout}")
        logger.error(f"Error output: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"[FAIL] Unexpected error in {description}: {e}")
        return False

def check_dependencies():
    """Check if required packages are installed."""
    logger.info("Checking dependencies...")
    
    required = ['playwright', 'pandas', 'streamlit', 'plotly', 'reportlab']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            logger.info(f"[OK] {package}")
        except ImportError:
            missing.append(package)
            logger.error(f"[MISSING] {package} not found")
    
    if missing:
        logger.error(f"\nMissing packages: {', '.join(missing)}")
        logger.error("Install with: pip install -r requirements.txt")
        return False
    
    logger.info("[OK] All dependencies installed")
    return True

def main():
    """Main pipeline execution."""
    start_time = datetime.now()
    
    logger.info("\n" + "="*70)
    logger.info("VINTED MARKET INTELLIGENCE PIPELINE")
    logger.info(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*70 + "\n")
    
    # Check dependencies
    if not check_dependencies():
        logger.error("[FAIL] Dependency check failed. Exiting.")
        sys.exit(1)
    
    # Create data directories
    Path("data/scrapes").mkdir(parents=True, exist_ok=True)
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    logger.info("[OK] Data directories ready\n")
    
    # Step 1: Run scraper
    success = run_command(
        [sys.executable, "vinted_scraper.py"],
        "SCRAPING (vinted_scraper.py)"
    )
    
    if not success:
        logger.error("[FAIL] Pipeline failed at scraping stage")
        sys.exit(1)
    
    # Step 2: Process data
    success = run_command(
        [sys.executable, "process_data.py"],
        "PROCESSING (process_data.py)"
    )
    
    if not success:
        logger.error("[FAIL] Pipeline failed at processing stage")
        sys.exit(1)
    
    # Step 3: Calculate KPIs
    success = run_command(
        [sys.executable, "calculate_kpis.py"],
        "CALCULATING KPIs (calculate_kpis.py)"
    )
    
    if not success:
        logger.warning("[WARN] KPI calculation had issues (normal on first run)")
        logger.info("Note: Full KPIs require at least 2 scrapes (48 hours apart)")
    
    # Summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    logger.info("\n" + "="*70)
    logger.info("PIPELINE COMPLETED")
    logger.info("="*70)
    logger.info(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Duration: {duration}")
    logger.info("="*70)
    
    # Check output files
    logger.info("\nOutput Files:")
    
    scrape_files = list(Path("data/scrapes").glob("vinted_scrape_*.csv"))
    if scrape_files:
        latest = sorted(scrape_files, key=lambda x: x.stat().st_mtime)[-1]
        logger.info(f"  [OK] Latest scrape: {latest.name}")
    else:
        logger.error("  [FAIL] No scrape files found")
    
    processed_files = {
        "listings.parquet": "Main listings database",
        "price_events.parquet": "Price changes",
        "sold_events.parquet": "Sold items"
    }
    
    for file, desc in processed_files.items():
        path = Path("data/processed") / file
        if path.exists():
            size = path.stat().st_size / 1024  # KB
            logger.info(f"  [OK] {file} ({size:.1f} KB) - {desc}")
        else:
            logger.warning(f"  [WARN] {file} not found - {desc}")
    
    # Next steps
    logger.info("\nNext Steps:")
    logger.info("  1. Test dashboard: streamlit run app.py")
    logger.info("  2. Wait 48 hours for second scrape")
    logger.info("  3. Run pipeline again to detect sold items")
    logger.info("  4. Deploy to Streamlit Cloud")
    logger.info("\n[OK] Pipeline execution complete!\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\n[INTERRUPT] Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n[FAIL] Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

def run_command(command, description):
    """Run a command and handle errors."""
    logger.info("="*70)
    logger.info(f"STEP: {description}")
    logger.info("="*70)
    
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(result.stdout)
        if result.stderr:
            logger.warning(result.stderr)
        logger.info(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed!")
        logger.error(f"Error: {e}")
        logger.error(f"Output: {e.stdout}")
        logger.error(f"Error output: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error in {description}: {e}")
        return False

def check_dependencies():
    """Check if required packages are installed."""
    logger.info("Checking dependencies...")
    
    required = ['playwright', 'pandas', 'streamlit', 'plotly', 'reportlab']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            logger.info(f"✅ {package}")
        except ImportError:
            missing.append(package)
            logger.error(f"❌ {package} not found")
    
    if missing:
        logger.error(f"\nMissing packages: {', '.join(missing)}")
        logger.error("Install with: pip install -r requirements.txt")
        return False
    
    logger.info("✅ All dependencies installed")
    return True

def main():
    """Main pipeline execution."""
    start_time = datetime.now()
    
    logger.info("\n" + "🚀 "*30)
    logger.info("VINTED MARKET INTELLIGENCE PIPELINE")
    logger.info(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("🚀 "*30 + "\n")
    
    # Check dependencies
    if not check_dependencies():
        logger.error("❌ Dependency check failed. Exiting.")
        sys.exit(1)
    
    # Create data directories
    Path("data/scrapes").mkdir(parents=True, exist_ok=True)
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    logger.info("✅ Data directories ready\n")
    
    # Step 1: Run scraper
    success = run_command(
        [sys.executable, "vinted_scraper.py"],
        "SCRAPING (vinted_scraper.py)"
    )
    
    if not success:
        logger.error("❌ Pipeline failed at scraping stage")
        sys.exit(1)
    
    # Step 2: Process data
    success = run_command(
        [sys.executable, "process_data.py"],
        "PROCESSING (process_data.py)"
    )
    
    if not success:
        logger.error("❌ Pipeline failed at processing stage")
        sys.exit(1)
    
    # Step 3: Calculate KPIs
    success = run_command(
        [sys.executable, "calculate_kpis.py"],
        "CALCULATING KPIs (calculate_kpis.py)"
    )
    
    if not success:
        logger.warning("⚠️  KPI calculation had issues (normal on first run)")
        logger.info("Note: Full KPIs require at least 2 scrapes (48 hours apart)")
    
    # Summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    logger.info("\n" + "="*70)
    logger.info("PIPELINE COMPLETED")
    logger.info("="*70)
    logger.info(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Duration: {duration}")
    logger.info("="*70)
    
    # Check output files
    logger.info("\n📁 Output Files:")
    
    scrape_files = list(Path("data/scrapes").glob("vinted_scrape_*.csv"))
    if scrape_files:
        latest = sorted(scrape_files, key=lambda x: x.stat().st_mtime)[-1]
        logger.info(f"  ✅ Latest scrape: {latest.name}")
    else:
        logger.error("  ❌ No scrape files found")
    
    processed_files = {
        "listings.parquet": "Main listings database",
        "price_events.parquet": "Price changes",
        "sold_events.parquet": "Sold items"
    }
    
    for file, desc in processed_files.items():
        path = Path("data/processed") / file
        if path.exists():
            size = path.stat().st_size / 1024  # KB
            logger.info(f"  ✅ {file} ({size:.1f} KB) - {desc}")
        else:
            logger.warning(f"  ⚠️  {file} not found - {desc}")
    
    # Next steps
    logger.info("\n🎯 Next Steps:")
    logger.info("  1. Test dashboard: streamlit run app.py")
    logger.info("  2. Wait 48 hours for second scrape")
    logger.info("  3. Run pipeline again to detect sold items")
    logger.info("  4. Deploy to Streamlit Cloud")
    logger.info("\n✅ Pipeline execution complete!\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)