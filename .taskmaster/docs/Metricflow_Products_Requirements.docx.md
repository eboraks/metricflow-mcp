# **Product Requirements Document: Natural Language to Charting Platform**

Version: 1.0  
Date: August 31, 2025  
Status: Draft

## **1\. Overview**

This document outlines the requirements for a Natural Language to Charting (NL2Chart) platform. The platform will enable non-technical users to generate data visualizations by typing queries in plain English. The system is designed with a modern, decoupled architecture, consisting of two distinct projects:

1. **Headless BI MCP Server:** A backend service that translates natural language into SQL queries and visualization specifications.  
2. **Chat UI with Charting Capabilities:** A web-based frontend that provides a conversational interface for users to interact with their data.

The primary goal is to create a secure, scalable, and intuitive business intelligence tool that empowers users to explore data without requiring knowledge of SQL or complex charting software.

## **2\. Project 1: Headless BI MCP Server**

### **2.1. Introduction**

The Headless BI Model Context Protocol (MCP) Server is the core engine of the platform. It is a stateless service that acts as a secure intermediary between the user's natural language query and the database. Its sole responsibility is to receive a query, orchestrate the translation process, execute the resulting SQL, and return a structured JSON payload containing the data and a visualization specification.

### **2.2. Functional Requirements**

| ID | Requirement | Description |
| :---- | :---- | :---- |
| **MCP-F1** | **NLQ API Endpoint** | The server MUST expose a primary API endpoint (/api/v1/query) that accepts a JSON object containing a natural language query and a data source identifier. |
| **MCP-F2** | **LLM Orchestration** | Upon receiving a query, the server orchestrates a multi-step process with a Large Language Model (LLM) to:  1\. Generate a secure, read-only SQL query based on the database schema.  2\. Generate a Vega-Lite JSON specification for visualizing the data. |
| **MCP-F3** | **Secure DB Execution** | The server executes the generated SQL query against the database specified by the dataSourceId. The connection use credentials that are securely stored and managed exclusively on the server. The database user have read-only permissions. |
| **MCP-F4** | **Data Source Management** | The server manage a list of pre-configured, trusted data sources. It expose another endpoint (/api/v1/datasources) that returns a list of available data source names and their IDs for the UI to display. |
| **MCP-F5** | **Contextual Follow-ups** | The server's API (/api/v1/query) needs be able to accept the previous vegaLiteSpec as context to handle follow-up queries like "make the bars red" or "change to a line chart." |
| **MCP-F6** | **Structured Response** | The server needs to return a single, well-structured JSON payload containing the original query, the generated SQL, the query results, and the Vega-Lite spec. See **Section 4: API Specification**. |
| **MCP-F7** | **Robust Error Handling** | The server needs to handle potential failures gracefully (e.g., invalid SQL from LLM, DB connection errors, malformed user requests) and return a structured error JSON payload. |
| **MCP-F8** | **Configure Datasource** | The server API will allow users to configure, edit and remove a datasource with: Create \- POST (/api/v1/datasource) Update \- PUT (/api/v1/datasource) Remove \- DELETE (/api/v1/datasource) |
|  |  |  |

### **2.3. Non-Functional Requirements**

| ID | Requirement | Description |
| :---- | :---- | :---- |
| **MCP-NF1** | **Security** | Database credentials MUST NOT be exposed in any API response. All database connections MUST use read-only users to prevent data modification. The system should be designed to mitigate the risk of SQL injection. |
| **MCP-NF2** | **Performance** | The P95 response time for a standard query (from request receipt to response delivery) should be under 5 seconds, excluding the time taken by the external database. |
| **MCP-NF3** | **Scalability** | The server MUST be stateless to allow for horizontal scaling behind a load balancer. |
| **MCP-NF4** | **Library For NL2SQL** | Identify an open source library that can improve the NL2SQL process |

## **3\. Project 2: Chat UI with Charting Capabilities** 

Note: Although the decision was made to focus on the headless MCP server, I included the requirements for the Chat UI to describe the vision of how a Chat UI will interact with the headless MCP.  

### **3.1. Introduction**

The Chat UI is a modern, responsive web application that serves as the primary user interface for the NL2Chart platform. It provides a familiar chat-based experience where users can type queries and see data visualizations rendered directly within the conversation flow.

### **3.2. Functional Requirements**

| ID | Requirement | Description |
| :---- | :---- | :---- |
| **UI-F1** | **Conversational Interface** | The UI will provide a text input for users to type natural language queries. The conversation history, including user prompts, text responses, and charts, will be displayed in a chronological, scrollable view. |
| **UI-F2** | **Chart Rendering** | The UI will dynamically render charts using the Vega-Lite specification received from the MCP Server's API. A dedicated charting library (e.g., vega-embed) will be used for this purpose. |
| **UI-F3** | **Interactive Charts** | Rendered charts SHOULD be interactive, supporting standard features like tooltips on hover. |
| **UI-F4** | **Data Source Selection** | The UI will include a settings or configuration area where the user can select their desired data source from a list fetched from the MCP Server's /api/v1/datasources endpoint. The selected dataSourceId must be sent with every query. |
| **UI-F5** | **MCP Server Configuration** | The UI must allow an administrator or user to configure the base URL for the Headless BI MCP Server it communicates with. |
| **UI-F6** | **State Management** | The UI must manage the state of the conversation. For follow-up queries, it needs to send the required context (e.g., the vegaLiteSpec from the previous successful response) back to the MCP server. |
| **UI-F7** | **Loading & Error States** | The UI must display a clear loading indicator while waiting for a response from the server. It also needs to display user-friendly error messages received from the server in the chat flow. |

### **3.3. Non-Functional Requirements**

| ID | Requirement | Description |
| :---- | :---- | :---- |
| **UI-NF1** | **Usability** | The interface should be clean, intuitive, and require no training for a user familiar with standard chat applications. |
| **UI-NF2** | **Responsiveness** | The application MUST be fully responsive and functional on both modern desktop and mobile web browsers. |

## **4\. API Specification (The Contract)**

This contract defines the communication protocol between the Chat UI (client) and the Headless BI MCP Server.

### **4.1. Endpoint: GET /api/v1/datasources**

* **Description:** Fetches the list of available data sources.  
* **Client:** Chat UI  
* **Server:** MCP Server  
* **Success Response (200 OK):**  
  {  
    "dataSources": \[  
      {  
        "id": "sales\_dw\_prod",  
        "name": "Sales Data Warehouse"  
      },  
      {  
        "id": "marketing\_db\_v2",  
        "name": "Marketing Analytics DB"  
      }  
    \]  
  }

### **4.2. Endpoint: POST /api/v1/query**

* **Description:** Submits a natural language query for processing.  
* **Client:** Chat UI  
* **Server:** MCP Server  
* **Request Body:**  
  {  
    "naturalLanguageQuery": "Show me total sales by region for the last quarter",  
    "dataSourceId": "sales\_dw\_prod",  
    "conversationContext": {  
      "previousVegaLiteSpec": {  
          // Vega-Lite JSON from the last response, sent for follow-up queries  
      }  
    }  
  }

  *Note: conversationContext and its properties are optional and only sent for follow-up queries.*  
* **Success Response (200 OK):**  
  {  
    "queryId": "b1b7a9f8-6e44-4b5a-8b0a-2b7e1c73b4a5",  
    "naturalLanguageResponse": "Here are the total sales by region for the last quarter.",  
    "sqlQuery": "SELECT region, SUM(sales) AS total\_sales FROM sales\_data WHERE order\_date \>= '2025-06-01' GROUP BY region;",  
    "vegaLiteSpec": {  
      "$schema": "\[https://vega.github.io/schema/vega-lite/v5.json\](https://vega.github.io/schema/vega-lite/v5.json)",  
      "description": "Total sales by region.",  
      "data": { "name": "values" },  
      "mark": "bar",  
      "encoding": {  
        "x": {"field": "region", "type": "nominal", "title": "Region"},  
        "y": {"field": "total\_sales", "type": "quantitative", "title": "Total Sales"}  
      }  
    },  
    "data": \[  
      {"region": "North", "total\_sales": 150000},  
      {"region": "South", "total\_sales": 125000},  
      {"region": "East", "total\_sales": 180000},  
      {"region": "West", "total\_sales": 165000}  
    \]  
  }

* **Error Response (400 Bad Request / 500 Internal Server Error):**  
  {  
    "queryId": "c2c8b0g9-7f55-5c6b-9c1b-3c8f2d84c5b6",  
    "error": "Could not process your request.",  
    "details": "The language model returned an invalid SQL query that failed to execute."  
  }

# **Dataset For Testing**

Uber ride data: [https://www.kaggle.com/datasets/yashdevladdha/uber-ride-analytics-dashboard](https://www.kaggle.com/datasets/yashdevladdha/uber-ride-analytics-dashboard)  
E-Commerce Site: [https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) 