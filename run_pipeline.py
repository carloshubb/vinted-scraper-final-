"""
Complete pipeline runner that executes scraping and data processing
"""
import logging
from datetime import datetime
import sys
from pathlib import Path

# Logging setup - Fixed for Windows encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'pipeline_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def run_full_pipeline():
    """Run the complete scraping and processing pipeline."""
    
    logger.info("="*70)
    logger.info("VINTED DATA PIPELINE - FULL RUN")
    logger.info("="*70)
    
    try:
        # Step 1: Run scraper
        logger.info("\n[1/2] Running Vinted scraper...")
        logger.info("-" * 70)
        
        from vinted_scraper import scrape_vinted
        scrape_vinted(headless=True, per_page=960)
        
        logger.info("OK Scraping completed successfully")
        
    except Exception as e:
        logger.error(f"ERROR Scraping failed: {e}")
        logger.error("Please check your scraper configuration")
        return False
    
    try:
        # Step 2: Process data
        logger.info("\n[2/2] Processing scraped data...")
        logger.info("-" * 70)
        
        from process_data import process_pipeline
        listings_df, price_events_df, sold_events_df = process_pipeline()
        
        logger.info("OK Data processing completed successfully")
        
    except Exception as e:
        logger.error(f"ERROR Data processing failed: {e}")
        logger.error("Check the scrape files and try running process_data.py separately")
        return False
    
    logger.info("\n" + "="*70)
    logger.info("OK PIPELINE COMPLETED SUCCESSFULLY!")
    logger.info("="*70)
    logger.info("\nGenerated files:")
    logger.info("  [DATA] data/processed/listings.parquet")
    logger.info("  [PRICES] data/processed/price_events.parquet")
    logger.info("  [SOLD] data/processed/sold_events.parquet")
    logger.info("\nNext steps:")
    logger.info("  1. Run this script again in 48 hours to detect changes")
    logger.info("  2. Use calculate_kpis.py to compute metrics")
    logger.info("  3. Launch dashboard with: streamlit run app.py")
    
    return True


def run_processing_only():
    """Run only the data processing step (if scrape already exists)."""
    logger.info("Running data processing only...")
    
    try:
        from process_data import process_pipeline
        process_pipeline()
        logger.info("OK Processing completed")
        return True
    except Exception as e:
        logger.error(f"ERROR Processing failed: {e}")
        return False


if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--process-only":
            run_processing_only()
        elif sys.argv[1] == "--scrape-only":
            from vinted_scraper import scrape_vinted
            scrape_vinted(headless=True, per_page=960)
        else:
            print("Usage:")
            print("  python run_pipeline.py              # Run full pipeline")
            print("  python run_pipeline.py --process-only   # Process existing scrape")
            print("  python run_pipeline.py --scrape-only    # Scrape only")
    else:
        run_full_pipeline()