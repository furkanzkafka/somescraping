import pandas as pd
import re


def clean_csv(input_file, output_file):
    # Read the CSV file
    df = pd.read_csv(input_file)

    # Remove empty rows
    df = df.dropna(how='all')

    # Function to clean email
    def clean_email(email):
        email = email.strip().lower()
        if re.match(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', email):
            return email
        return None

    # Keep track of seen emails to avoid duplicates
    seen_emails = set()
    new_rows = []

    for _, row in df.iterrows():
        if pd.isna(row['Emails Found']) or row['Emails Found'] == 'No emails found':
            continue

        # Split emails and clean each one
        emails = row['Emails Found'].split(',')
        cleaned_emails = [clean_email(email) for email in emails]
        # Remove None values and already seen emails
        cleaned_emails = [email for email in cleaned_emails if email and email not in seen_emails]

        # Create a new row for each unique email and add to seen emails
        for email in cleaned_emails:
            seen_emails.add(email)
            new_rows.append({
                'Website': row['Website'],
                'Page URL': row['Page URL'],
                'Emails Found': email
            })

    # Create new dataframe from the expanded rows
    clean_df = pd.DataFrame(new_rows)

    # Sort by website and email
    clean_df = clean_df.sort_values(['Website', 'Emails Found'])

    # Save cleaned data
    clean_df.to_csv(output_file, index=False)

    print(f"Cleaned file saved as {output_file}")
    print(f"Found {len(clean_df)} unique email entries")

    # Print results grouped by website
    print("\nResults by website:")
    for website in clean_df['Website'].unique():
        emails = clean_df[clean_df['Website'] == website]['Emails Found'].tolist()
        print(f"\n{website}:")
        for email in emails:
            print(f"  - {email}")


# Example usage
clean_csv('company_emails.csv', 'cleaned_emails.csv')
