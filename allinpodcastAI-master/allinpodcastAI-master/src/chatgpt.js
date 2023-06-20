import axios from "axios";
export const getChatGptResponse = async (message) => {
  const response = await axios.post('http://localhost:5000/api/chat', {
    message: message,
  });

  // Extract the bot response from the backend response
  const botResponse = response.data.message;
  console.log(botResponse)
  return botResponse;
};