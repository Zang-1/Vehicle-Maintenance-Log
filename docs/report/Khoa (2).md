# SYSTEM ANALYSIS AND DESIGN REPORT

## Assigned Work: Activity Diagram and Architecture & Class Diagram

## 1. Overview of Assigned Work

The assigned work in this project focuses on two main modules:

-   **M4 -- Service Types:** Management of the service-type catalog.
-   **M6 -- Statistics:** Management of the dashboard and cost
    statistics.

In addition to analyzing the functions of these two modules, this report
explains how the related functions are represented in the Activity
Diagram, the system architecture, and the data components in the Class
Diagram.

The content is based on File 03 (Activity Diagram) and File 07
(Architecture & Class Diagram). Any information that is not clearly
supported by these documents is not added as an existing system feature.

## 2. Business Function Analysis

### 2.1. Module M4 -- Service Types

#### 2.1.1. Objective

Module M4 is responsible for managing the catalog of maintenance and
repair service types. This catalog is used as a source of selectable
data in related business processes, such as creating maintenance records
and setting reminders.

#### 2.1.2. Main Functions

The module provides the following functions:

-   View the list of service types.
-   Filter the list by active status.
-   Add a new service type.
-   Update service-type information.

According to business rule BR-09, a service type cannot be deleted
directly. Instead, it is changed to an inactive status. Inactive service
types are no longer available for selection in workflows that require a
service type.

#### 2.1.3. Managed Data

The input information for a service type is represented by
`ServiceTypeIn`, which includes the following attributes:

  -----------------------------------------------------------------------
  Attribute                           Description
  ----------------------------------- -----------------------------------
  `name`                              Name of the service type

  `description`                       Description of the service type

  `applies_to`                        Applicable vehicle type:
                                      `MOTORBIKE`, `CAR`, or `ALL`

  `default_interval_km`               Default maintenance reminder
                                      interval in kilometers

  `default_interval_months`           Default maintenance reminder
                                      interval in months

  `is_active`                         Active status
  -----------------------------------------------------------------------

`ServiceTypeOut` contains the input attributes and adds an `id`
attribute to identify the service-type record.

#### 2.1.4. Processing Operations

The `service_types` router provides the following operations:

-   `list_service_types(active)`: Retrieves the list of service types
    and can filter the results by active status.
-   `create_service_type(body)`: Creates a new service type using the
    submitted data.
-   `update_service_type(id, body)`: Updates service-type information
    based on its identifier.

The module stores its data in the `service_types` table.

#### 2.1.5. Related Functional Requirements

Module M4 is responsible for the following requirements:

-   **FR-11:** Manage the service-type catalog.
-   **FR-12:** Update service-type information.

### 2.2. Module M6 -- Statistics

#### 2.2.1. Objective

Module M6 provides overview information and cost statistics, allowing
users to monitor service usage and vehicle maintenance expenses.

#### 2.2.2. Main Functions

The functions described in the design include:

-   Display overview information on the dashboard.
-   Generate cost statistics by group.
-   Filter statistical data by a date range.

#### 2.2.3. Output Data

`DashboardOut` is the data model used by the dashboard. It includes:

  Attribute               Description
  ----------------------- ----------------------------------
  `vehicle_count`         Number of vehicles
  `cost_this_month`       Total cost for the current month
  `attention_reminders`   Reminders that require attention
  `recent_records`        Recent records

`CostRow` represents one row of cost-statistics data and includes:

  Attribute      Description
  -------------- ----------------------------------------
  `label`        Name of the statistical group or label
  `total_cost`   Corresponding total cost

#### 2.2.4. Processing Operations

The `stats` router provides the following operations:

-   `dashboard()`: Retrieves overview data for the dashboard.
-   `costs(group_by, from_date, to_date)`: Retrieves cost-statistics
    data according to the specified grouping criterion and date range.

The statistics module retrieves data from the following views:

-   `v_record_totals`
-   `v_reminder_status`

Cost data is grouped by service type, and the costs of the corresponding
maintenance items are summed.

#### 2.2.5. Related Functional Requirements

Module M6 is responsible for:

-   **FR-16:** Dashboard and overview information.
-   **FR-17:** Cost statistics.

## 3. Activity Diagram Related to the Modules

File 03 presents the system's Activity Diagram. It does not contain
separate Activity Diagrams specifically dedicated to M4 and M6.
Therefore, this section describes the roles of the two modules in the
related workflows shown in the document. It does not present these
descriptions as newly added diagrams from the original file.

### 3.1. M4 -- Service Types in Business Workflows

The service-type catalog is used in workflows where users need to select
a service type.

**In the maintenance-record creation workflow:**

1.  The user starts the process of recording maintenance information.
2.  The system loads the list of active service types.
3.  The user selects an appropriate service type.
4.  The user continues entering the required record information.
5.  The system processes and saves the information according to the
    recording workflow.

**In the reminder-creation workflow:**

1.  The user starts creating a reminder.
2.  The system identifies the related vehicle type.
3.  The system loads active service types that are applicable to that
    vehicle type.
4.  The user selects a service type.
5.  The user continues configuring the reminder information.

Therefore, M4 provides catalog data for use by other workflows.
Displaying only active service types helps prevent users from selecting
service types that are no longer in use.

### 3.2. M6 -- Statistics in the Dashboard and Statistics Workflow

The M6 workflow focuses on retrieving data and displaying summarized
information:

1.  The user accesses the dashboard or statistics function.
2.  The interface sends a request to the system.
3.  The `stats` router receives the corresponding request.
4.  The system queries data from the designed database views.
5.  The data is aggregated into dashboard information or a list of cost
    statistics.
6.  The system returns the data to the interface.
7.  The interface displays the overview indicators and statistical
    results.

For cost statistics, the request may include a grouping criterion
(`group_by`) and a date range (`from_date`, `to_date`). The system uses
these criteria to retrieve the relevant data.

## 4. Architecture -- System Architecture

### 4.1. Technologies Used

According to File 07, the system uses the following technologies and
tools:

  Component                               Technology
  --------------------------------------- -----------------------
  Programming language                    Python 3.12
  Backend framework                       FastAPI
  Data validation and modeling            Pydantic v2
  Template engine                         Jinja2
  Frontend                                HTML, CSS, JavaScript
  Database connection                     psycopg3
  Database management system              PostgreSQL 16
  Containerization                        Podman/Docker
  Deployment                              Render/Supabase
  Continuous integration and deployment   GitHub Actions
  Source-code management                  GitHub

### 4.2. Three-Layer Architecture

The system is organized using a three-layer architecture:

#### a. Presentation Layer

The presentation layer uses HTML, CSS, JavaScript, and Jinja2 to build
the pages with which users interact.

For M4, this layer provides the interface for displaying the
service-type list and performing operations such as adding and updating
service-type information.

For M6, this layer displays the dashboard, overview indicators, and
cost-statistics results.

#### b. Logic Layer

The logic layer uses FastAPI to receive and process requests from the
interface. Pydantic is used to model and validate input and output data.

-   For M4, the `service_types` router handles requests to retrieve the
    list, create new service types, and update existing service types.
-   For M6, the `stats` router handles requests to retrieve dashboard
    data and cost statistics.

#### c. Data Layer

The data layer uses PostgreSQL to store and provide system data. The
application connects to the database through psycopg3.

-   M4 operates on the `service_types` table.
-   M6 retrieves data from the `v_record_totals` and `v_reminder_status`
    views.

### 4.3. Data Communication Flow

The system's general processing flow is as follows:

1.  The user interacts with the interface.
2.  The frontend sends a request to the backend.
3.  FastAPI receives the request through the corresponding router.
4.  The data is validated and processed by the logic and schema
    components.
5.  The backend queries or updates data in PostgreSQL.
6.  The result is returned to the frontend.
7.  The interface displays the result to the user.

## 5. Class Diagram and Related Components

### 5.1. M4 Data Models

**`ServiceTypeIn`**

Represents the input data used when creating or updating a service type.
Its attributes include the name, description, applicable vehicle type,
default interval in kilometers, default interval in months, and active
status.

**`ServiceTypeOut`**

Represents the service-type data returned by the system. In addition to
the attributes of `ServiceTypeIn`, this model includes an `id` attribute
to identify the record.

**`AppliesTo`**

This is the set of values representing the applicability of a service
type. It includes:

-   `MOTORBIKE`
-   `CAR`
-   `ALL`

### 5.2. M6 Data Models

**`DashboardOut`**

The output data model for the dashboard. It includes the number of
vehicles, the cost for the current month, reminders requiring attention,
and recent records.

**`CostRow`**

The model representing cost-statistics data for each label or group. It
includes `label` and `total_cost`.

### 5.3. Routers and Operations

  ---------------------------------------------------------------------------------------
  Module                  Router                  Operation
  ----------------------- ----------------------- ---------------------------------------
  M4 -- Service Types     `service_types`         `list_service_types(active)`

  M4 -- Service Types     `service_types`         `create_service_type(body)`

  M4 -- Service Types     `service_types`         `update_service_type(id, body)`

  M6 -- Statistics        `stats`                 `dashboard()`

  M6 -- Statistics        `stats`                 `costs(group_by, from_date, to_date)`
  ---------------------------------------------------------------------------------------

**Note:** In the design, the routers and operations above are described
as Python application modules and functions. Therefore, they should not
all be interpreted as classes in the traditional object-oriented
programming sense.

## 6. Evaluation and Conclusion

The assigned work focuses on two modules: M4 and M6. M4 manages the
service-type catalog and provides shared data for workflows such as
recording maintenance and creating reminders. M6 retrieves system data
to provide overview information and cost statistics.

In terms of architecture, the system is divided into three layers:
presentation, business logic, and data. This organization separates the
responsibilities of displaying information, processing requests, and
storing data. The data models `ServiceTypeIn`, `ServiceTypeOut`,
`DashboardOut`, and `CostRow` define the data structures exchanged
between system components.

When comparing the report with the provided documents, it is important
to note that File 03 does not contain separate Activity Diagrams
specifically for M4 and M6. Therefore, this report only describes the
involvement of the two modules in related business workflows. This
approach clarifies the assigned scope of work without attributing
diagrams or functions to the original design when they are not shown in
the source documents.
