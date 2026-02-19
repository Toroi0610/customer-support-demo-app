package com.example.customersupport.adapter

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.customersupport.R
import com.example.customersupport.model.Message
import com.example.customersupport.model.MessageType
import java.text.SimpleDateFormat
import java.util.Locale

class MessageAdapter : ListAdapter<Message, RecyclerView.ViewHolder>(MessageDiffCallback()) {

    companion object {
        private const val VIEW_TYPE_USER = 0
        private const val VIEW_TYPE_AGENT = 1
        private const val VIEW_TYPE_SYSTEM = 2
        private const val VIEW_TYPE_TOOL = 3
    }

    override fun getItemViewType(position: Int): Int {
        return when (getItem(position).type) {
            MessageType.USER -> VIEW_TYPE_USER
            MessageType.AGENT -> VIEW_TYPE_AGENT
            MessageType.SYSTEM -> VIEW_TYPE_SYSTEM
            MessageType.TOOL -> VIEW_TYPE_TOOL
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
        val inflater = LayoutInflater.from(parent.context)
        return when (viewType) {
            VIEW_TYPE_USER -> UserMessageViewHolder(
                inflater.inflate(R.layout.item_message_user, parent, false)
            )
            VIEW_TYPE_AGENT -> AgentMessageViewHolder(
                inflater.inflate(R.layout.item_message_agent, parent, false)
            )
            VIEW_TYPE_SYSTEM -> SystemMessageViewHolder(
                inflater.inflate(R.layout.item_message_system, parent, false)
            )
            else -> ToolMessageViewHolder(
                inflater.inflate(R.layout.item_message_system, parent, false)
            )
        }
    }

    override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
        val message = getItem(position)
        val timeFormat = SimpleDateFormat("HH:mm", Locale.getDefault())
        val timeStr = timeFormat.format(message.timestamp)

        when (holder) {
            is UserMessageViewHolder -> holder.bind(message, timeStr)
            is AgentMessageViewHolder -> holder.bind(message, timeStr)
            is SystemMessageViewHolder -> holder.bind(message)
            is ToolMessageViewHolder -> holder.bind(message)
        }
    }

    inner class UserMessageViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val tvContent: TextView = itemView.findViewById(R.id.tv_message_content)
        private val tvTime: TextView = itemView.findViewById(R.id.tv_message_time)

        fun bind(message: Message, time: String) {
            tvContent.text = message.content
            tvTime.text = time
        }
    }

    inner class AgentMessageViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val tvContent: TextView = itemView.findViewById(R.id.tv_message_content)
        private val tvTime: TextView = itemView.findViewById(R.id.tv_message_time)

        fun bind(message: Message, time: String) {
            tvContent.text = message.content
            tvTime.text = time
        }
    }

    inner class SystemMessageViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val tvContent: TextView = itemView.findViewById(R.id.tv_system_message)

        fun bind(message: Message) {
            tvContent.text = message.content
        }
    }

    inner class ToolMessageViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val tvContent: TextView = itemView.findViewById(R.id.tv_system_message)

        fun bind(message: Message) {
            tvContent.text = message.content
        }
    }
}

class MessageDiffCallback : DiffUtil.ItemCallback<Message>() {
    override fun areItemsTheSame(oldItem: Message, newItem: Message): Boolean {
        return oldItem.id == newItem.id
    }

    override fun areContentsTheSame(oldItem: Message, newItem: Message): Boolean {
        return oldItem == newItem
    }
}
