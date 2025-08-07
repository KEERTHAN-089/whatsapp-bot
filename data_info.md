# Data Storage Information
> **Applicability for Render.com:**  
> The described storage approach works for simple deployments on Render.com, as long as the application root directory is writable. However, note that Render's disk storage is ephemeral—data may be lost on redeploys or restarts. For persistent storage, consider using a managed database or external storage service.
## Current Implementation

The WhatsApp Catering Bot stores data in two ways:

1. **In-memory storage** during runtime:
   - All work opportunities, worker selections, and admin states are stored in memory while the application is running.

2. **Persistent JSON file storage**:
   - Data is saved to `catering_data.json` after every request
   - Data is loaded from this file when the application starts
   - Backups can be created using the `/backup` endpoint

## File Locations

- **Main data file**: `catering_data.json` in the application root directory
- **Backup files**: `catering_data_backup_YYYYMMDD_HHMMSS.json` in the application root directory

## Data Structure

The JSON file contains:
- A dictionary of work opportunities (keyed by work_id)
- The current active work ID
- For backups, a timestamp of when the backup was created

## Limitations

This simple file-based storage has some limitations:
- No concurrency control for multiple writes
- Limited scalability for very large datasets
- No built-in data recovery mechanisms

## Future Enhancements

For a production environment, consider upgrading to:
- A SQLite database (simple, still file-based but more robust)
- PostgreSQL or MySQL (for larger scale deployments)
- Cloud-based database services

## Manually Backing Up Data

You can trigger a manual backup by:
1. Running your application
2. Visiting the `/backup` endpoint in a browser
3. The system will create a timestamped backup file

## Restoring from Backup

To restore from a backup:
1. Rename your backup file to `catering_data.json`
2. Restart the application
