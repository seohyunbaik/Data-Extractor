import os
import pandas as pd
from datetime import datetime, timedelta

# Define the types of data
data_types = {
    'Basic_Data': 1,
    'Countdown_Data': 2,
    'Advice_go_stop_Date': 3,
    'Advice_go_stop_Date_Only': 4,
    'Loading_Data': 5,
    'OutOfService_Data': 6
}

# Paths to the data folder and desktop for Windows
participants_data_path = r'C:\Users\user\Desktop\Participants original data'
desktop_path = r'C:\Users\user\Desktop'

def determine_trial_type(file_name):
    for key in data_types:
        if key in file_name:
            return data_types[key]
    return None

def extract_timestamp(file_name):
    parts = file_name.split('_')
    if len(parts) < 3:
        print(f"Invalid filename structure: {file_name}")
        return None

    try:
        # Extract the timestamp part
        timestamp_str = '_'.join(parts[-2:]).replace('.csv', '')
        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d_%H-%M-%S')
        return timestamp
    except ValueError as e:
        print(f"Error parsing timestamp from file: {file_name}, error: {e}")
        return None

def calculate_metrics_using_time(df):
    start_time = df['Time'].iloc[0]
    three_seconds_later = start_time + 3
    six_seconds_later = start_time + 6

    # Pre-filter data to avoid repetitive filtering
    data_up_to_3s = df[df['Time'] <= three_seconds_later]
    data_up_to_6s = df[df['Time'] <= six_seconds_later]
    data_3s_to_6s = data_up_to_6s[data_up_to_6s['Time'] > three_seconds_later]

    max_acceleration_time = df.loc[df['Acceleration'].idxmax(), 'Time']

    metrics = {
        "Stop/go": int(df['BrakeTorque'].abs().max() > 0),
        "Initial speed": df['Speed'].iloc[0],
        "Initial distanceToStopLine": df['DistanceToStopLine_U'].iloc[0],
        "Average speed": df['Speed'].mean(),
        "Average speed (During the green signal)": data_up_to_3s['Speed'].mean(),
        "Average speed (During yellow light)": data_3s_to_6s['Speed'].mean(),
        "Average speed (During green+yellow light)": data_up_to_6s['Speed'].mean(),
        "Deviation of speed from speed limit (total)": df['Speed'].mean() - 50,
        "Deviation of speed from speed limit (During the green signal)": data_up_to_3s['Speed'].mean() - 50,
        "Deviation of speed from speed limit (During yellow light)": data_3s_to_6s['Speed'].mean() - 50,
        "Deviation of speed from speed limit (During green+yellow light)": data_up_to_6s['Speed'].mean() - 50,
        "Maximum acceleration (first 10s)": df[df['Time'] <= start_time + 10]['Acceleration'].max(),
        "Maximum deceleration (first 10s)": df[df['Time'] <= start_time + 10]['Acceleration'].min(),
        "Maximum acceleration (Total)": df['Acceleration'].max(),
        "Maximum deceleration (Total)": df['Acceleration'].min(),
        "Maximum acceleration (Total) (During the green signal)": data_up_to_3s['Acceleration'].max(),
        "Maximum acceleration (Total) (During yellow light)": data_3s_to_6s['Acceleration'].max(),
        "Maximum acceleration (Total) (During green+yellow light)": data_up_to_6s['Acceleration'].max(),
        "Maximum deceleration (Total) (During the green signal)": data_up_to_3s['Acceleration'].min(),
        "Maximum deceleration (Total) (During yellow light)": data_3s_to_6s['Acceleration'].min(),
        "Maximum deceleration (Total) (During green+yellow light)": data_up_to_6s['Acceleration'].min(),
        "Steer Angle (Total)": df['SteerAngle'].mean(),
        "Steer Angle (During the green signal)": data_up_to_3s['SteerAngle'].mean(),
        "Steer Angle (During yellow light)": data_3s_to_6s['SteerAngle'].mean(),
        "Steer Angle (first 10s)": df[df['Time'] <= start_time + 10]['SteerAngle'].mean(),
        "YawRate (Total)": df['YawRate'].mean(),
        "YawRate (During the green signal)": data_up_to_3s['YawRate'].mean(),
        "YawRate (During yellow light)": data_3s_to_6s['YawRate'].mean(),
        "YawRate (first 10s)": df[df['Time'] <= start_time + 10]['YawRate'].mean(),
        "Heading error (Total)": df['HeadingError'].mean(),
        "Heading error (During the green signal)": data_up_to_3s['HeadingError'].mean(),
        "Heading error (During yellow light)": data_3s_to_6s['HeadingError'].mean(),
        "Heading error (first 10s)": df[df['Time'] <= start_time + 10]['HeadingError'].mean(),
        "Speed at 3s": data_up_to_3s['Speed'].iloc[-1] if not data_up_to_3s.empty else None,
        "Speed at 6s": data_up_to_6s['Speed'].iloc[-1] if not data_up_to_6s.empty else None,
        "Distance to stop line at 3s": data_up_to_3s['DistanceToStopLine_U'].iloc[-1] if not data_up_to_3s.empty else None,
        "Distance to stop line at 6s": data_up_to_6s['DistanceToStopLine_U'].iloc[-1] if not data_up_to_6s.empty else None,
        "Maximum mtorque": df['MotorTorque'].min(),
        "Maximum btorque": df['BrakeTorque'].min(),
        "Time to maximum acceleration": max_acceleration_time - start_time
    }

    metrics["Run red light"] = int(metrics["Stop/go"] == 0 and metrics["Distance to stop line at 6s"] > 0)

    # Calculate time-based metrics
    for i, row in df.iterrows():
        if row['BrakeTorque'] != 0 and 'Brake reaction time' not in metrics:
            metrics['Brake reaction time'] = row['Time'] - start_time
        if row['Speed'] == 0 and 'Time to speed = 0' not in metrics:
            metrics['Time to speed = 0'] = row['Time'] - start_time
            metrics['Stop position'] = row['DistanceToStopLine_U']
            metrics['Maximum deceleration (stop)'] = df['Acceleration'][:i+1].min()
            metrics['Time to maximum deceleration (stop)'] = df.loc[df['Acceleration'][:i+1].idxmin(), 'Time'] - start_time

    return metrics

def process_csv_file(file_path, trial_type, participant_no, trial_no, interaction):
    columns = [
        "NO", "Trial", "Interaction No", "Trial type", "Time to stop line", "Initial speed",
        "Speed at 3s", "Speed at 6s", "Average speed", "Average speed (During the green signal)",
        "Average speed (During yellow light)", "Average speed (During green+yellow light)",
        "Deviation of speed from speed limit (total)", "Deviation of speed from speed limit (During the green signal)",
        "Deviation of speed from speed limit (During yellow light)", "Deviation of speed from speed limit (During green+yellow light)",
        "Initial distanceToStopLine", "Distance to stop line at 3s", "Distance to stop line at 6s", "Stop/go",
        "Maximum acceleration (first 10s)", "Maximum acceleration (Total)", "Maximum acceleration (Total) (During the green signal)",
        "Maximum acceleration (Total) (During yellow light)", "Maximum acceleration (Total) (During green+yellow light)",
        "Run red light", "Time to maximum acceleration", "Maximum mtorque", "Brake reaction time", "Maximum deceleration (first 10s)",
        "Maximum deceleration (Total)", "Maximum deceleration (Total) (During the green signal)", "Maximum deceleration (Total) (During yellow light)",
        "Maximum deceleration (Total) (During green+yellow light)", "Time to speed = 0", "Stop position", "Maximum deceleration (stop)",
        "Time to maximum deceleration (stop)", "Maximum btorque", "Steer Angle (first 10s)", "Steer Angle (During the green signal)",
        "Steer Angle (During yellow light)", "Steer Angle (Total)", "YawRate (first 10s)", "YawRate (During the green signal)",
        "YawRate (During yellow light)", "YawRate (Total)", "Heading error (first 10s)", "Heading error (During the green signal)",
        "Heading error (During yellow light)", "Heading error (Total)", "Stop/go advice"
    ]

    try:
        # Calculate metrics
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.strip()
        metrics = calculate_metrics_using_time(df)

        # Calculate Time to stop line
        initial_speed = metrics["Initial speed"]
        initial_distance_to_stop_line = metrics["Initial distanceToStopLine"]
        time_to_stop_line = round(initial_distance_to_stop_line / initial_speed) if initial_speed > 0 else None

        new_row = {
            "NO": participant_no,
            "Trial": trial_no,
            "Interaction No": interaction,
            "Trial type": trial_type,
            "Time to stop line": time_to_stop_line,
            **metrics
        }

        # Convert the new_row to a DataFrame
        return pd.DataFrame([new_row], columns=columns)
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return pd.DataFrame(columns=columns)

def stack_csv_files(directory):
    # Initialize a list to store the combined data
    combined_data = []

    # Gather and sort participant folders
    participant_folders = sorted([f for f in os.listdir(directory) if os.path.isdir(os.path.join(directory, f)) and f.startswith('P')], key=lambda x: int(x[1:]))

    # Print found participant folders
    print("Found participant folders:")
    for participant_folder in participant_folders:
        print(participant_folder)

    # Iterate through participant folders
    for participant_folder in participant_folders:
        participant_path = os.path.join(directory, participant_folder)
        participant_no = int(participant_folder[1:])
        print(f"\nProcessing participant {participant_no}")

        # Get a list of all CSV files in the participant's folder
        all_files = [(os.path.join(participant_path, f), f) for f in os.listdir(participant_path) if f.endswith('.csv')]

        # Filter and sort files by timestamp
        sorted_files = sorted(
            [(path, name, extract_timestamp(name)) for path, name in all_files if extract_timestamp(name) is not None],
            key=lambda x: x[2]
        )

        trial_no = 1
        interaction_no = 1

        # Previous file name for detecting trial change
        prev_file_name = None

        # Header for the log output
        print(f"{'Filename':<60} | {'Participant':<12} | {'Trial':<6} | {'Trial type':<10} | {'Interaction':<11}")
        print("="*100)

        # Iterate through files and assign trial numbers
        for file_path, file_name, _ in sorted_files:
            trial_type = determine_trial_type(file_name)
            if trial_type is not None:
                if prev_file_name and determine_trial_type(prev_file_name) != trial_type:
                    trial_no += 1
                    interaction_no = 1

                if interaction_no > 6:
                    trial_no += 1
                    interaction_no = 1

                if trial_no > 6:
                    break  # If we reach more than 6 trials, we stop processing for the participant

                file_data = process_csv_file(file_path, trial_type, participant_no, trial_no, interaction_no)
                combined_data.append(file_data)
                interaction_no += 1

                print(f"{file_name:<60} | {participant_no:<12} | {trial_no:<6} | {trial_type:<10} | {interaction_no-1:<11}")

                prev_file_name = file_name

    if not combined_data:
        print("No valid data to process.")
        return None

    try:
        # Concatenate all DataFrames
        combined_data_df = pd.concat(combined_data, ignore_index=True)

        # Save the combined data to an Excel file on the desktop
        output_file = os.path.join(desktop_path, 'combined_data.xlsx')
        combined_data_df.to_excel(output_file, index=False)

        return output_file
    except Exception as e:
        print(f"Error saving combined data: {e}")
        return None

# Call the function to process and combine CSV files in the specified directory
output_file = stack_csv_files(participants_data_path)
if output_file:
    print(f'Combined data saved to: {output_file}')
else:
    print('No valid data found.')
