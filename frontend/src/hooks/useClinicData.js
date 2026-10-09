"use client";

import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';

/**
 * Loads the reference data + KPI stats that every page needs.
 * One source of truth so the dashboard, booking modal and filters always
 * agree about which doctors and patients exist.
 */
export function useReferenceData() {
  const [doctors, setDoctors] = useState([]);
  const [patients, setPatients] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [backendUp, setBackendUp] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [doctorList, patientList, statsData] = await Promise.all([
        api.listDoctors(),
        api.listPatients(),
        api.getStats(),
      ]);
      setDoctors(doctorList);
      setPatients(patientList);
      setStats(statsData);
      setBackendUp(true);
    } catch (err) {
      setError(err);
      setBackendUp(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Poll the liveness endpoint so the sidebar indicator reflects reality.
  useEffect(() => {
    let stopped = false;
    const check = () => {
      api
        .health()
        .then(() => !stopped && setBackendUp(true))
        .catch(() => !stopped && setBackendUp(false));
    };
    const timer = setInterval(check, 15000);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, []);

  return { doctors, patients, stats, loading, error, backendUp, reload: load };
}

const EMPTY_FILTERS = {
  status: '',
  doctor_id: '',
  date_from: '',
  date_to: '',
  upcoming_only: '',
};

/**
 * Loads the appointment list for the given filters.
 * `onChanged` fires after a mutation so the page can refresh the KPI stats.
 */
export function useAppointments(filters = {}, onChanged) {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        status: filters.status || undefined,
        doctor_id: filters.doctor_id || undefined,
        date_from: filters.date_from
          ? new Date(`${filters.date_from}T00:00:00`).toISOString()
          : undefined,
        date_to: filters.date_to
          ? new Date(`${filters.date_to}T23:59:59`).toISOString()
          : undefined,
        upcoming_only: filters.upcoming_only || undefined,
        limit: 100,
      };
      setAppointments(await api.listAppointments(params));
    } catch (err) {
      setError(err);
      setAppointments([]);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    load();
  }, [load]);

  const refreshAll = useCallback(async () => {
    await Promise.all([load(), onChanged?.()]);
  }, [load, onChanged]);

  const advance = useCallback(
    async (id, status) => {
      setBusyId(id);
      try {
        await api.changeStatus(id, status);
        await refreshAll();
      } catch (err) {
        setError(err);
      } finally {
        setBusyId(null);
      }
    },
    [refreshAll],
  );

  const cancel = useCallback(
    async (id) => {
      setBusyId(id);
      try {
        await api.cancelAppointment(id);
        await refreshAll();
      } catch (err) {
        setError(err);
      } finally {
        setBusyId(null);
      }
    },
    [refreshAll],
  );

  return {
    appointments,
    loading,
    error,
    busyId,
    reload: refreshAll,
    advance,
    cancel,
  };
}

export { EMPTY_FILTERS };