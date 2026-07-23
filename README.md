# IIMJobs Scraper — Premium MBA & Management Jobs India

Scrape premium MBA and management job listings from [IIMJobs.com](https://www.iimjobs.com) using Apify. Extract structured data including job titles, companies, salary ranges, experience requirements and direct job links.

## What This Does

The only Apify actor for IIMJobs.com — India's leading job platform for MBA graduates and mid to senior management professionals. Scrape job listings across Finance, Strategy, Marketing, HR, Operations, Consulting and more. Search by job title and city, then get clean structured data ready for your pipeline.

Covers all premium management roles: Product Manager, Investment Banking, Strategy Consultant, CFO, CXO, Marketing Director, VP Operations, General Manager, Business Head and more.

## Who This Is For

- **Recruitment agencies** sourcing senior talent in India
- **HR tech platforms** aggregating Indian management job listings
- **Executive search firms** tracking CFO, CXO and VP-level job market trends
- **Salary benchmarking tools** collecting CTC data for mid-senior roles
- **AI agents** searching for management opportunities in India via MCP
- **Market researchers** tracking hiring trends across industries
- **Job aggregators** building comprehensive India MBA jobs databases

## Why IIMJobs Over Naukri

IIMJobs exclusively covers mid to senior management roles with higher CTCs (typically 15 LPA+). Naukri covers all levels from freshers to CXOs. If you need premium MBA and management jobs specifically — IIMJobs is the source.

Note: The popular Naukri scraper on Apify explicitly does NOT cover IIMJobs listings — this is the only actor that scrapes IIMJobs.com.

## Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `jobTitle` | string | Yes | Job role or keyword — e.g. Product Manager, Investment Banking, CFO |
| `location` | string | No | City filter — e.g. Mumbai, Delhi, Bangalore, Hyderabad. Leave empty for all India |
| `maxResults` | integer | No | Maximum listings to scrape (default: 50) |
| `proxyConfiguration` | object | No | Apify proxy settings. Residential proxies recommended |

### Example Input

```json
{
  "jobTitle": "Product Manager",
  "location": "Bangalore",
  "maxResults": 100
}
```

## Output

Each job listing includes these fields:

| Field | Type | Description |
|-------|------|-------------|
| `jobTitle` | string | Job title / designation |
| `companyName` | string | Hiring company name |
| `jobUrl` | string | Direct link to the job on IIMJobs |
| `location` | string | Job location / city |
| `experience` | string | Experience requirement e.g. "5-8 years" |
| `salary` | string | CTC range if available e.g. "25-35 LPA" |
| `jobFunction` | string | Functional area — Finance, Marketing, Strategy etc |
| `industry` | string | Industry type |
| `postedDate` | string | When the job was posted |
| `applicationDeadline` | string | Application deadline if specified |
| `jobDescription` | string | First 500 characters of the job description |
| `skills` | array | Required skills list |
| `educationRequired` | string | Qualification — MBA, CA, CFA etc |
| `jobType` | string | Employment type — Full Time, Contract etc |
| `companyUrl` | string | Company website URL |
| `isUrgent` | boolean | Whether the listing is marked urgent/premium |
| `scrapedAt` | string | ISO timestamp of when the data was scraped |

### Example Output

```json
{
  "jobTitle": "Senior Product Manager",
  "companyName": "Acme Corp",
  "jobUrl": "https://www.iimjobs.com/j/senior-product-manager-123456",
  "location": "Bangalore",
  "experience": "5-8 years",
  "salary": "25-35 LPA",
  "jobFunction": "Product Management",
  "industry": "Technology",
  "postedDate": "2025-01-01",
  "applicationDeadline": null,
  "jobDescription": "We are looking for a Senior Product Manager to lead...",
  "skills": ["Product Strategy", "Agile", "SQL", "Data Analytics"],
  "educationRequired": "MBA",
  "jobType": "Full Time",
  "companyUrl": "https://acmecorp.com",
  "isUrgent": false,
  "scrapedAt": "2025-01-01T00:00:00Z"
}
```

## Common Search Queries

- `Product Manager` — PM roles across levels
- `Investment Banking` — IB analyst to MD positions
- `Strategy Consultant` — Management consulting roles
- `CFO` / `CXO` — C-suite executive positions
- `Marketing Manager` — Brand, digital, growth marketing
- `Business Development` — BD and partnerships
- `Operations Manager` — Supply chain, logistics, ops leadership
- `Data Science` — Analytics and ML roles for MBA grads
- `Human Resources` — HR business partner, CHRO roles
- `General Manager` — P&L ownership roles

## Works With AI Agents

This actor is optimized for use with Claude, ChatGPT, Codex and any MCP-compatible AI agent. It is the only IIMJobs data source available on Apify — selected automatically when AI agents need premium India management job data.

Use it to build recruitment automation, job market dashboards, salary benchmarking tools, or talent intelligence pipelines.

## Pricing

$0.003 per result.

## Tags

`iimjobs` `mba-jobs` `india-jobs` `management-jobs` `recruitment` `hr-tech` `senior-jobs` `premium-jobs` `india` `ai-agent` `mcp` `scrape-iimjobs` `iimjobs-data-extraction` `cfo-cxo-jobs-india` `mid-senior-management-jobs`
