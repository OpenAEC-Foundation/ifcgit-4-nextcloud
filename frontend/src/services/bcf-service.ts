/**
 * BCF API client - Phase 2 implementation.
 */

import api from "./api";

export const bcfApi = {
  listTopics(projectId: string) {
    return api.get(`/bcf/3.0/projects/${projectId}/topics`);
  },
  createTopic(projectId: string, data: any) {
    return api.post(`/bcf/3.0/projects/${projectId}/topics`, data);
  },
  getTopic(projectId: string, guid: string) {
    return api.get(`/bcf/3.0/projects/${projectId}/topics/${guid}`);
  },
  updateTopic(projectId: string, guid: string, data: any) {
    return api.put(`/bcf/3.0/projects/${projectId}/topics/${guid}`, data);
  },
  listComments(projectId: string, guid: string) {
    return api.get(`/bcf/3.0/projects/${projectId}/topics/${guid}/comments`);
  },
  createComment(projectId: string, guid: string, data: any) {
    return api.post(`/bcf/3.0/projects/${projectId}/topics/${guid}/comments`, data);
  },
};
