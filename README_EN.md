# Climbing Score Counting System

A real-time leaderboard application system based on "reverse score distribution" logic.

**English** | **[中文](README.md)**

## Project Overview

This system uses Python/Django as the backend framework and SQLite (default) or MySQL as the database, implementing real-time scoring and leaderboard functionality for climbing competitions.

### Core Scoring Formula

- **Normal Group**: Single route score $S_r = \frac{L}{P_r}$ (where $L$ is the total score per route, $P_r$ is the number of normal group members who completed route $r$)
- **Custom Group**: Each completed route earns a fixed $L$ points, not shared with other members

### Automatic Calculation of Total Score Per Route (L)

- **Members < 8**: Use Least Common Multiple (LCM) of 1 to member count
- **Members ≥ 8**: Fixed at 1000 points
- **No normal members**: Default to 1 point

## Technology Stack

- **Backend**: Python 3.8+ / Django 4.2
- **Database**: SQLite (default) or MySQL 5.7+ (optional)
- **API**: Django REST Framework
- **Frontend**: HTML + CSS + JavaScript
- **Image Processing**: Pillow (supports mobile photo uploads)
- **HTML Parsing**: BeautifulSoup4 (for HTML structure checking in tests)

## Quick Start

### One-Click Start (Recommended)

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Startup Script**:
   
   **Windows PowerShell**:
   ```powershell
   .\start_server.ps1
   ```
   
   **Windows CMD**:
   ```cmd
   start_server.bat
   ```
   
   **Linux/macOS**:
   ```bash
   chmod +x start_server.sh
   ./start_server.sh
   ```

   The startup script will automatically:
   - ✅ Run database migrations
   - ✅ Start the server

3. **Access the System**:
   - **Homepage**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/) (Create rooms, view room list)
   - **Leaderboard Page**: [http://127.0.0.1:8000/leaderboard/{room_id}/](http://127.0.0.1:8000/leaderboard/{room_id}/) (Manage members, routes, view leaderboard)
   - **Rules Page**: [http://127.0.0.1:8000/rules/](http://127.0.0.1:8000/rules/) (View scoring rules)
   - **Admin Panel**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

## Detailed Setup

### Environment Requirements

- Python 3.8+
- SQLite (default, no installation needed) or MySQL 5.7+ (optional)
- pip

### Manual Setup Steps

For detailed manual setup instructions, please refer to the `SETUP.md` file.

Main steps include:
1. Install dependencies
2. Configure database (default uses SQLite)
3. Run migrations
4. Start the server

**Note**: All data (rooms, members, routes) must be created through the web interface. The system does not provide command-line data initialization functionality.

## API Endpoints

### Get Leaderboard

```
GET /api/rooms/{room_id}/leaderboard/
```

Response format:
```json
{
  "room_info": {
    "name": "Room Name",
    "standard_line_score": 12,
    "id": 1
  },
  "leaderboard": [
    {
      "id": 1,
      "name": "Member Name",
      "is_custom_calc": false,
      "total_score": "48.00",
      "completed_routes_count": 5
    }
  ]
}
```

### Create Room

```
POST /api/rooms/
```

Request body format:
```json
{
  "name": "Room Name"
}
```

**Note**: `standard_line_score` (total score per route) is automatically calculated based on the number of normal group members and does not need to be set manually.

### Add Member

```
POST /api/members/
```

Request body format:
```json
{
  "room": 1,
  "name": "Member Name",
  "is_custom_calc": false
}
```

**Note**: Member names must be unique within the same room.

### Update Member

```
PATCH /api/members/{member_id}/
```

Request body format:
```json
{
  "name": "New Member Name",
  "is_custom_calc": true
}
```

**Note**:
- Can update only some fields (name, is_custom_calc)
- When updating member name, it must still be unique within the same room
- Changing member group (is_custom_calc) will automatically trigger score updates

### Delete Member

```
DELETE /api/members/{member_id}/
```

Deleting a member will automatically trigger score updates.

### Create Route

```
POST /api/rooms/{room_id}/routes/
```

Request body format (JSON):
```json
{
  "name": "Route 1",
  "grade": "V4",
  "member_completions": {
    "1": true,
    "2": false,
    "3": true
  }
}
```

Request body format (FormData, supports photo upload):
```
name: Route 1
grade: V4
photo: [file]
member_completions: {"1":true,"2":false}
```

**Note**:
- Difficulty level (grade) is required, range: V1-V8+
- Route name will automatically have 【路線】prefix added
- Supports photo uploads (mobile devices can take photos directly)

### Update Route

```
PATCH /api/routes/{route_id}/
```

Request body format (JSON):
```json
{
  "name": "Route 1",
  "grade": "V5",
  "member_completions": {
    "1": true,
    "2": false,
    "3": true
  }
}
```

Request body format (FormData, supports photo upload):
```
name: Route 1
grade: V5
photo: [file]
member_completions: {"1":true,"2":false,"3":true}
```

**Note**:
- Can update only some fields (name, grade, member_completions, photo)
- `member_completions` is in JSON string format, keys are member IDs (strings), values are booleans
- Members not specified in `member_completions` will have their completion status set to `false`
- Supports photo updates (uploading a new photo will overwrite the old one)

### Update Score Status

```
PATCH /api/scores/{score_id}/
```

Request body format:
```json
{
  "is_completed": true
}
```

### Delete Route

```
DELETE /api/routes/{route_id}/
```

Deleting a route will automatically trigger score updates.

## Database Structure

### Room
- `name`: Room name
- `standard_line_score`: Total score per route (L), automatically calculated based on normal group member count
  - Members < 8: LCM(1,2,...,N)
  - Members ≥ 8: Fixed 1000
  - No normal members: Default 1

### Member
- `room`: Foreign key to Room
- `name`: Member name (must be unique within the same room)
- `is_custom_calc`: Whether it's a custom group
- `total_score`: Total score (automatically calculated)

### Route
- `room`: Foreign key to Room
- `name`: Route name (automatically has 【路線】prefix added)
- `grade`: Difficulty level (V1-V8+, required)
- `photo`: Photo file (ImageField)
- `photo_url`: Photo URL (legacy, deprecated)

### Score
- `member`: Foreign key to Member
- `route`: Foreign key to Route
- `is_completed`: Whether completed
- `score_attained`: Points earned (automatically calculated)

## Scoring Logic

The core scoring logic is implemented in the `update_scores(room_id)` function in `scoring/models.py`.

### Trigger Events

- When creating a route
- When updating route member completion status
- When updating score status
- When deleting a route
- When adding/deleting/updating members
- When changing member group (normal/custom)

### Calculation Process

1. Get the room's standard line score $L$
2. For each route, calculate the number of normal group members who completed it $P_r$
3. Calculate route score $S_r = L / P_r$ (if $P_r > 0$)
4. Distribute scores to normal group members who completed the route
5. Count routes completed by custom group members, calculate total score (route count × $L$)
6. Update all members' `total_score`

## Testing

### Run Tests

```bash
# Run all tests
python manage.py test scoring.tests

# Run specific test case
python manage.py test scoring.tests.test_api.APITestCase.test_create_room_add_member_create_route
```

### Test Cases

The system includes the following test cases (31 test files, over 250 test cases):

1. **Core Scoring Logic Tests** (`test_case_01_default_member.py`):
   - Progressive route addition scoring
   - Score updates when marking complete/incomplete
   - Score recalculation after route deletion
   - Independent score calculation for custom and normal groups

2. **API Endpoint Tests** (`test_api.py`):
   - Get leaderboard
   - Create route
   - Update score status
   - Complete workflow test (create room, add member, create route)
   - Get member completed routes list

3. **Progressive Route Completion Tests** (`test_case_route_progressive_completion.py`):
   - Route created with no completions
   - One member completes later
   - Another member completes later
   - Verify completion count and score calculation

4. **Route Name Edit Tests** (`test_case_route_name_edit.py`):
   - Edit route name (no change)
   - Edit route name (change to number)
   - Edit route name (change to text)
   - Verify API returns correct route name

5. **Route Completion Status Update Tests** (`test_case_route_update_completions.py`):
   - Mark two members as completed
   - Unmark completed members
   - Partial member completion status updates
   - Empty completion status handling
   - Verify score updates

6. **FormData Format Tests** (`test_case_route_update_with_formdata.py`):
   - Use FormData to mark members as completed
   - Use FormData to unmark
   - FormData handling for partial checkboxes
   - Verify API response structure

7. **Complete Route Creation Flow Tests** (`test_api.py`):
   - Create route with multiple completed members
   - Verify frontend displays correct completion count
   - Simulate complete frontend flow (create → immediate refresh)

8. **Route Photo Upload Tests** (`test_case_route_photo_upload.py`):
   - Create route with photo upload
   - Create route without photo (should work normally)
   - Update route to add photo (originally no photo)
   - Update route to replace photo (originally has photo)
   - Update route without updating photo (keep original photo)
   - Get route and verify photo_url is correctly returned

9. **Route Photo Thumbnail Display Tests** (`test_case_route_photo_thumbnail.py`):
   - Routes with photos display thumbnails in route list
   - Routes without photos do not display thumbnails
   - Thumbnail updates after route photo update
   - Multiple routes (with and without photos) display thumbnails correctly

10. **Mobile UI Tests** (`test_case_mobile_ui.py`):
   - Page contains viewport meta tag
   - Mobile leaderboard page loads correctly
   - Mobile API responses work correctly
   - Mobile FormData route creation (simulating mobile upload)
   - Mobile create route with photo upload (detailed verification)
   - Mobile update route to add photo (originally no photo)
   - Mobile update route to replace photo (originally has photo)
   - Mobile upload different image formats (PNG, JPEG, HEIC)
   - Mobile upload photo and verify photo_url (test multiple mobile browsers)
   - Mobile route update
   - Mobile get member completed routes list
   - Mobile page contains responsive design elements
   - CSS file contains mobile media queries
   - Mobile form input font size (prevent iOS auto-zoom)

11. **Security Tests** (`test_case_12_security.py`)

12. **Settings Configuration Tests** (`test_case_13_settings_config.py`)

13. **Login UI Tests** (`test_case_14_login_ui.py`)

14. **AWS Deployment Issues Tests** (`test_case_15_aws_deployment_issues.py`)

15. **iPhone Photo Upload Tests** (`test_case_16_iphone_photo_upload.py`)

16. **Mobile Photo Upload Tests** (`test_case_17_mobile_photo_upload.py`)

17. **Route Photo Display Tests** (`test_case_18_route_photo_display.py`)

18. **Mobile Delete Route Tests** (`test_case_19_mobile_delete_route.py`)

19. **First Time Camera Photo Tests** (`test_case_20_first_time_camera_photo.py`)

20. **Mobile Desktop Data Consistency Tests** (`test_case_21_mobile_desktop_data_consistency.py`)

21. **iPhone Photo Update Route Fix Tests** (`test_case_22_iphone_photo_update_route_fix.py`)

22. **Desktop Route Update Authentication Tests** (`test_case_23_desktop_route_update_authentication.py`)

23. **Member Deletion Leaderboard Tests** (`test_case_24_member_deletion_leaderboard.py`)

24. **Guest Create Room CSRF Tests** (`test_case_25_guest_create_room_csrf.py`)

25. **Create Route with Photo Tests** (`test_case_26_create_route_with_photo.py`)

26. **Room Deletion Tests** (`test_case_27_room_deletion.py`)

27. **Tab Switching Tests** (`test_case_27_tab_switching.py`)

28. **Boundary Values Tests** (`test_case_28_boundary_values.py`)

29. **Safari Route List Alignment Tests** (`test_case_28_safari_route_list_alignment.py`):
   - Safari browser route list left alignment
   - Route names do not wrap unexpectedly
   - Route list frame left alignment

30. **Data Integrity Tests** (`test_case_29_data_integrity.py`)

31. **Safari Detailed Alignment Diagnostic Tests** (`test_case_29_safari_detailed_alignment.py`):
   - Detailed CSS property value checks for each element
   - HTML structure and inline style checks
   - JavaScript-generated HTML checks
   - Mobile-specific style override checks
   - Safari-specific compatibility checks (including -webkit- prefixes)

32. **Add Member to Existing Routes Tests** (`test_case_30_add_member_to_existing_routes.py`)

### GitHub Actions Testing

The project is configured with GitHub Actions for automated testing. Tests run automatically on every code push. See `.github/workflows/test.yml`.

Tests run on multiple Python versions (3.8, 3.9, 3.10, 3.11, 3.12) to ensure compatibility.

## Development and Maintenance

### Admin Panel

Access `/admin/` to use the Django admin panel to manage all data.

**First-time use**: Create a superuser:
```bash
python manage.py createsuperuser
```

### Adding Test Data

All data must be created through the web interface:
- **Homepage** (`/`): Create rooms
- **Leaderboard Page** (`/leaderboard/{room_id}/`): Add members, create routes
- **Admin Panel** (`/admin/`): Manage all data

**Note**: The system does not provide command-line data initialization functionality. All data must be created through the web interface.

### Issue Fix Records

Fixed issues are documented in the `issue_fixed/` folder:
- `issue_01_create_route_completion_count_zero_flow_analysis.md` - Detailed flow analysis
- `issue_01_create_route_completion_count_zero_fix_report.md` - Fix report

**Naming Convention**: Same issue uses the same number (e.g., `issue_01`), different document types use different suffixes (`flow_analysis`, `fix_report`).

### Test Helpers

The system provides a `scoring/tests/test_helpers.py` module with reusable test data creation functions:

- **`TestDataFactory`**: Provides convenient methods for creating rooms, members, and routes
- **`cleanup_test_data()`**: Unified test data cleanup (deletes rooms and all related data)
- **`create_basic_test_setup()`**: One-click basic test setup creation

All tests use `cleanup_test_data()` in their `tearDown` methods to ensure clean test environments.

### Code Standards

- All debug logging code has been removed
- Code simplified, only core logic and necessary comments retained
- Test code uses helper modules for improved maintainability
- Temporary files and test output files have been added to `.gitignore`

## License

This project is for learning and development purposes only.

