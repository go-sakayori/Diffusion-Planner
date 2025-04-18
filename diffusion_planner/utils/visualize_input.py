import matplotlib.pyplot as plt
import numpy as np
import torch
from pathlib import Path
from diffusion_planner.utils.normalizer import ObservationNormalizer
from copy import deepcopy


def visualize_inputs(inputs: dict, obs_normalizer: ObservationNormalizer, save_path: Path):
    """
    draw the input data of the diffusion_planner model on the xy plane
    """
    inputs = deepcopy(inputs)
    inputs = obs_normalizer.inverse(inputs)

    # Function to convert PyTorch tensors to NumPy arrays
    def to_numpy(tensor):
        if isinstance(tensor, torch.Tensor):
            return tensor.detach().cpu().numpy()
        return tensor

    for key in inputs:
        inputs[key] = to_numpy(inputs[key])

    """
    key='ego_current_state', inputs[key].shape=(1, 10)
    key='neighbor_agents_past', inputs[key].shape=(1, 32, 21, 11)
    key='lanes', inputs[key].shape=(1, 70, 20, 12)
    key='lanes_speed_limit', inputs[key].shape=(1, 70, 1)
    key='lanes_has_speed_limit', inputs[key].shape=(1, 70, 1)
    key='route_lanes', inputs[key].shape=(1, 25, 20, 12)
    key='route_lanes_speed_limit', inputs[key].shape=(1, 25, 1)
    key='route_lanes_has_speed_limit', inputs[key].shape=(1, 25, 1)
    key='static_objects', inputs[key].shape=(1, 5, 10)
    key='sampled_trajectories', inputs[key].shape=(1, 11, 81, 4)
    key='diffusion_time', inputs[key].shape=(1,)
    """

    # initialize the figure
    fig, ax = plt.subplots(figsize=(10, 8))

    # ==== Ego ====
    ego_state = inputs["ego_current_state"][0]  # Use the first sample in the batch
    ego_x, ego_y = ego_state[0], ego_state[1]
    ego_heading = np.arctan2(ego_state[3], ego_state[2])
    ego_vel_x = ego_state[4]
    ego_vel_y = ego_state[5]
    ego_acc_x = ego_state[6]
    ego_acc_y = ego_state[7]
    ego_steering = ego_state[8]
    ego_yaw_rate = ego_state[9]

    # Ego vehicle's length and width
    car_length = 4.5  # Assumed value for vehicle length
    car_width = 2.0  # Assumed value for vehicle width
    dx = car_length / 2 * np.cos(ego_heading)
    dy = car_length / 2 * np.sin(ego_heading)

    # Draw the ego vehicle as an arrow
    ax.arrow(
        ego_x,
        ego_y,
        dx,
        dy,
        width=car_width / 2,
        head_width=car_width,
        head_length=car_length / 3,
        fc="r",
        ec="r",
        alpha=0.7,
        label="Ego Vehicle",
    )

    # ==== Neighbor agents ====
    neighbors = inputs["neighbor_agents_past"][0]  # Use the first sample in the batch
    last_timestep = neighbors.shape[1] - 1

    for i in range(neighbors.shape[0]):
        neighbor = neighbors[i, last_timestep]

        # Skip zero vectors (masked objects)
        if np.sum(np.abs(neighbor[:4])) < 1e-6:
            continue

        n_x, n_y = neighbor[0], neighbor[1]
        n_heading = np.arctan2(neighbor[3], neighbor[2])
        vel_x, vely = neighbor[4], neighbor[5]
        len_x, len_y = neighbor[6], neighbor[7]

        # Set color and shape dimensions based on the vehicle type
        vehicle_type = np.argmax(neighbor[8:11]) if neighbor.shape[0] > 8 else 0
        if vehicle_type == 0:  # Vehicle
            color = "blue"
        elif vehicle_type == 1:  # Pedestrian
            color = "green"
        else:  # Bicycle
            color = "purple"

        # Draw the past trajectory as a dashed line
        past_x = [neighbors[i, t, 0] for t in range(last_timestep + 1)]
        past_y = [neighbors[i, t, 1] for t in range(last_timestep + 1)]
        ax.plot(past_x, past_y, color=color, alpha=0.9, linestyle="--")

        # Draw the current position as an arrow
        dx = len_x / 2 * np.cos(n_heading)
        dy = len_y / 2 * np.sin(n_heading)
        ax.arrow(
            n_x,
            n_y,
            dx,
            dy,
            width=len_y / 2,
            head_width=len_y,
            head_length=len_x / 3,
            fc=color,
            ec=color,
            alpha=0.5,
        )
        ax.text(
            n_x + 10,
            n_y,
            f"Agent {i}",
            fontsize=8,
            color=color,
            ha="center",
            va="center",
        )

        # Draw bounding box
        ax.add_line(
            plt.Line2D(
                [n_x - dx, n_x + dx],
                [n_y - dy, n_y + dy],
                color=color,
                alpha=0.5,
            )
        )
        ax.add_line(
            plt.Line2D(
                [n_x - dx, n_x + dx],
                [n_y + dy, n_y - dy],
                color=color,
                alpha=0.5,
            )
        )
        ax.add_line(
            plt.Line2D(
                [n_x - dx, n_x - dx],
                [n_y - dy, n_y + dy],
                color=color,
                alpha=0.5,
            )
        )
        ax.add_line(
            plt.Line2D(
                [n_x + dx, n_x + dx],
                [n_y - dy, n_y + dy],
                color=color,
                alpha=0.5,
            )
        )

    # ==== Static objects ====
    static_objects = inputs["static_objects"][0]  # Use the first sample in the batch

    for i in range(static_objects.shape[0]):
        obj = static_objects[i]

        # Skip zero vectors (masked objects)
        if np.sum(np.abs(obj[:4])) < 1e-6:
            continue

        obj_x, obj_y = obj[0], obj[1]
        obj_heading = np.arctan2(obj[3], obj[2])
        obj_width = obj[4] if obj.shape[0] > 4 else 1.0
        obj_length = obj[5] if obj.shape[0] > 5 else 1.0

        # Set color based on the object type
        obj_type = np.argmax(obj[-4:]) if obj.shape[0] >= 10 else 0
        colors = ["orange", "gray", "yellow", "brown"]
        obj_color = colors[obj_type % len(colors)]

        # Draw the object as a rectangle
        rect = plt.Rectangle(
            (obj_x - obj_length / 2, obj_y - obj_width / 2),
            obj_length,
            obj_width,
            angle=np.degrees(obj_heading),
            color=obj_color,
            alpha=0.4,
        )
        ax.add_patch(rect)

    # ==== Lanes ====
    lanes = inputs["lanes"][0]  # Use the first sample in the batch
    lanes_speed_limit = inputs["lanes_speed_limit"][0]
    lanes_has_speed_limit = inputs["lanes_has_speed_limit"][0]

    for i in range(lanes.shape[0]):
        for j in range(lanes.shape[1]):
            lane_point = lanes[i, j]
            traffic_light = lane_point[8:12]
            color = None
            if traffic_light[0] == 1:
                color = "green"
            elif traffic_light[1] == 1:
                color = "yellow"
            elif traffic_light[2] == 1:
                color = "red"
            elif traffic_light[3] == 1:
                color = "gray"

            # Skip zero vectors (masked objects)
            if np.sum(np.abs(lane_point[:4])) < 1e-6:
                continue

            # the lane boundaries
            left_x = lane_point[0] + lane_point[4]
            left_y = lane_point[1] + lane_point[5]

            right_x = lane_point[0] + lane_point[6]
            right_y = lane_point[1] + lane_point[7]

            if j + 1 < lanes.shape[1]:
                next_point = lanes[i, j + 1]
                ax.plot(
                    [lane_point[0], next_point[0]],
                    [lane_point[1], next_point[1]],
                    alpha=0.1,
                    linewidth=1,
                    color=color,
                )
                next_left_x = next_point[0] + next_point[4]
                next_left_y = next_point[1] + next_point[5]
                ax.plot(
                    [left_x, next_left_x],
                    [left_y, next_left_y],
                    alpha=0.25,
                    linewidth=1,
                    color=color,
                )

                next_right_x = next_point[0] + next_point[6]
                next_right_y = next_point[1] + next_point[7]
                ax.plot(
                    [right_x, next_right_x],
                    [right_y, next_right_y],
                    alpha=0.25,
                    linewidth=1,
                    color=color,
                )
        # print speed limit
        # ax.text(
        #     (left_x + next_left_x) / 2,
        #     (left_y + next_left_y) / 2,
        #     f"Limit({lanes_has_speed_limit[i][0]})={lanes_speed_limit[i][0]:.1f}",
        #     fontsize=8,
        #     color=color,
        # )

    # ==== Route ====
    route_lanes = inputs["route_lanes"][0]  # Use the first sample in the batch
    route_lanes_speed_limit = inputs["route_lanes_speed_limit"][0]
    route_lanes_has_speed_limit = inputs["route_lanes_has_speed_limit"][0]

    for i in range(route_lanes.shape[0]):
        skipped = []
        for j in range(route_lanes.shape[1]):
            lane_point = route_lanes[i, j]
            # Skip zero vectors (masked objects)
            if np.sum(np.abs(lane_point[:4])) < 1e-6:
                skipped.append(True)
                continue
            skipped.append(False)
            traffic_light = lane_point[8:12]
            color = None
            if traffic_light[0] == 1:
                color = "green"
            elif traffic_light[1] == 1:
                color = "yellow"
            elif traffic_light[2] == 1:
                color = "red"
            elif traffic_light[3] == 1:
                color = "gray"

            # the lane boundaries
            left_x = lane_point[0] + lane_point[4]
            left_y = lane_point[1] + lane_point[5]

            right_x = lane_point[0] + lane_point[6]
            right_y = lane_point[1] + lane_point[7]

            if j + 1 < route_lanes.shape[1]:
                next_point = route_lanes[i, j + 1]
                ax.plot(
                    [lane_point[0], next_point[0]],
                    [lane_point[1], next_point[1]],
                    alpha=0.5,
                    linewidth=2,
                    color=color,
                )
                next_left_x = next_point[0] + next_point[4]
                next_left_y = next_point[1] + next_point[5]
                ax.plot(
                    [left_x, next_left_x],
                    [left_y, next_left_y],
                    alpha=0.5,
                    linewidth=2,
                    color=color,
                )

                next_right_x = next_point[0] + next_point[6]
                next_right_y = next_point[1] + next_point[7]
                ax.plot(
                    [right_x, next_right_x],
                    [right_y, next_right_y],
                    alpha=0.5,
                    linewidth=2,
                    color=color,
                )
        # print speed limit
        # ax.text(
        #     (left_x + next_left_x) / 2,
        #     (left_y + next_left_y) / 2,
        #     f"Limit({route_lanes_has_speed_limit[i][0]})={route_lanes_speed_limit[i][0]:.1f}",
        #     fontsize=8,
        #     color="black",
        # )

        num_skipped = sum(skipped)
        if num_skipped != 0 and num_skipped != 20:
            print(f"{num_skipped}")
            exit(0)

        # print index
        if num_skipped != 20:
            ax.text(
                (left_x + next_left_x) / 2,
                (left_y + next_left_y) / 2,
                f"Route{i}",
                fontsize=8,
                color="black",
            )

    # プロットの装飾
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)

    # 自車両の速度・加速度・舵角などをテキストで表示
    ax.text(
        99,
        99,
        f"VelocityX: {ego_vel_x:.2f} m/s\n"
        f"VelocityY: {ego_vel_y:.2f} m/s\n"
        f"AccelerationX: {ego_acc_x:.2f} m/s²\n"
        f"AccelerationY: {ego_acc_y:.2f} m/s²\n"
        f"Steering: {ego_steering:.2f} rad\n"
        f"Yaw Rate: {ego_yaw_rate:.2f} rad/s",
        fontsize=8,
        color="red",
        ha="right",
        va="top",
    )

    # エゴ車両中心の表示範囲を設定
    view_range = 110
    ax.set_xlim(ego_x - view_range, ego_x + view_range)
    ax.set_ylim(ego_y - view_range, ego_y + view_range)

    # 凡例を追加
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(loc="upper right")

    plt.tight_layout()

    # 保存
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close()
