"""Generate sample job postings for testing."""

import argparse
import json
import random
import time
from hashlib import sha256
from pathlib import Path

# store the generated job postings in the job_postings directory
OUTPUT_DIR = Path("job_postings")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

company_name_starts = [
    "Agile",
    "Cloud",
    "Code",
    "Data",
    "Dev",
    "Info",
    "Innova",
    "Innovate",
    "Logic",
    "Quick",
    "Rev",
    "Soft",
    "Tech",
    "Web",
    "Cyber",
    "Full",
    "IT",
    "Machine",
    "Mobile",
]

company_name_ends = [
    "AI",
    "Craft",
    "Edge",
    "Flow",
    "Link",
    "Net",
    "Prime",
    "Soft",
    "Solve",
    "Sync",
    "Sys",
    "Tech",
    "Tek",
    "Ware",
    "Works",
    "X",
    "Z",
    "Y",
]

companies = [f"{start}{end}" for start in company_name_starts for end in company_name_ends]

titles = [
    "Junior Frontend Developer",
    "Senior Backend Engineer",
    "Data Scientist",
    "Product Manager",
    "UX Designer",
    "DevOps Engineer",
    "Machine Learning Engineer",
    "Software Architect",
    "Security Analyst",
    "Cloud Solutions Architect",
    "QA Engineer",
    "Technical Writer",
    "Systems Engineer",
    "Network Administrator",
    "Database Administrator",
    "Business Analyst",
    "Scrum Master",
    "IT Support Specialist",
    "Full Stack Developer",
    "AI Research Scientist",
    "Cybersecurity Specialist",
    "Web Developer",
    "Mobile App Developer",
    "Systems Analyst",
    "Network Engineer",
    "Software Engineer",
    "Data Engineer",
    "Technical Project Manager",
    "UI/UX Designer",
    "Cloud Engineer",
    "Product Designer",
    "Data Analyst",
    "Software Developer",
    "IT Manager",
    "IT Director",
    "CTO",
    "CIO",
    "CEO",
    "COO",
    "CFO",
    "VP of Engineering",
    "VP of Product",
    "VP of Marketing",
    "VP of Sales",
    "VP of Operations",
    "VP of Finance",
    "VP of HR",
    "VP of IT",
    "VP of Business Development",
    "VP of Customer Success",
    "VP of Partnerships",
    "VP of Strategy",
    "VP of Analytics",
    "VP of Research",
    "VP of Compliance",
    "VP of Legal",
    "VP of Administration",
    "VP of Services",
    "VP of Support",
    "VP of Training",
    "VP of Quality",
    "VP of Procurement",
    "VP of Logistics",
    "VP of Supply Chain",
    "VP of Manufacturing",
    "VP of Distribution",
    "VP of Retail",
    "VP of E-commerce",
    "VP of Real Estate",
    "VP of Construction",
]

locations = [
    "Boston, MA",
    "San Francisco, CA",
    "New York, NY",
    "Austin, TX",
    "Seattle, WA",
    "Chicago, IL",
]


def generate_job_posting(timestamp: int) -> dict:
    """Generates a single job posting.

    Returns:
        dict: A single job posting.
    """
    company = random.choice(companies)  # noqa: S311
    title = random.choice(titles)  # noqa: S311
    location = random.choice(locations)  # noqa: S311
    return {
        "url": f"https://www.{company.lower()}.ai/job/{sha256(f"{company}\t{title}".encode()).hexdigest()}/",
        "company": company,
        "title": title,
        "location": location,
        "scraped_on": timestamp,
    }


def generate_job_postings(num_postings: int, postings_per_file: int, start_timestamp: int) -> None:
    """Generates job postings and writes them into files."""
    current_timestamp = start_timestamp

    for i in range(0, num_postings, postings_per_file):
        postings = []

        for j in range(postings_per_file):
            if i + j >= num_postings:
                break  # stop generating more data than required

            job_posting = generate_job_posting(current_timestamp)
            postings.append(job_posting)

            # increment timestamp for each posting
            current_timestamp += random.randint(0, 1)  # noqa: S311

        # store data in a timestamped file
        filename = OUTPUT_DIR / f"{postings[-1]["scraped_on"]}.jsonl"
        with filename.open(mode="w") as file:
            for posting in postings:
                file.write(json.dumps(posting) + "\n")

        print(f"Generated file: {filename}")


def main() -> None:
    """Main function to generate job postings."""
    parser = argparse.ArgumentParser(description="Generate job postings and store them in files.")

    parser.add_argument(
        "--total",
        type=int,
        default=18_000,
        help="Total number of job postings to generate (default: 18,000)",
    )
    parser.add_argument(
        "--split",
        type=int,
        default=6_000,
        help="Number of postings per file (default: 6,000)",
    )

    args = parser.parse_args()

    total = args.total
    split = args.split
    start_timestamp = int(time.time())  # start timestamp at current time

    generate_job_postings(total, split, start_timestamp)


if __name__ == "__main__":
    main()
